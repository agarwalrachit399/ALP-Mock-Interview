import asyncio
import json
import logging
import random
import time
import uuid
import threading
from datetime import datetime
from typing import Dict, Optional, Set
from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect, WebSocketState

# Import all the services we'll orchestrate
from app.services.moderation_service import ModerationService
from app.services.followup_service import followup_service
from app.services.stt_service import stt_service
from app.services.tts_service import tts_service
from app.services.session_memory import session_memory_manager
from app.core.config import settings
from app.models.session import InterviewConfig, SessionStats, SessionMessage
from app.models.followup import FollowupRequest, ShouldGenerateRequest
from app.core.database import sessions_collection

logger = logging.getLogger(__name__)

class LPSelector:
    """Leadership Principle selector"""
    def __init__(self, lp_questions: dict):
        self.lp_questions = lp_questions
        self.asked = set()

    def pick_new_lp(self):
        remaining = list(set(self.lp_questions.keys()) - self.asked)
        if not remaining:
            return None
        lp = random.choice(remaining)
        self.asked.add(lp)
        return lp

class SessionManager:
    """Session timing and ID management"""
    def __init__(self):
        self.session_id = str(uuid.uuid4())
        self.start_time = None

    def start_session(self):
        self.start_time = time.time()

    def time_remaining(self, limit):
        if not self.start_time:
            return limit
        return limit - (time.time() - self.start_time)

    def get_session_id(self):
        return self.session_id

    def get_elapsed_time(self):
        if not self.start_time:
            return 0
        return time.time() - self.start_time

class InteractionLogger:
    """Database logging for interview interactions"""
    def __init__(self, user_id: str):
        self.user_id = user_id

    def log_lp_block(self, session_id: str, lp: str, main_question: str, main_answer: str, followups: list):
        """Log a complete LP block to database"""
        try:
            from app.core.database import check_database_health, sessions_collection
            
            if not check_database_health():
                logger.warning("⚠️ [DB] Database unavailable - LP block not logged")
                return
            
            doc = {
                "session_id": session_id,
                "user_id": self.user_id,
                "principle": lp,
                "main_question": {
                    "question": main_question,
                    "answer": main_answer
                },
                "followups": followups,
                "timestamp": datetime.now().isoformat()
            }
            sessions_collection.insert_one(doc)
            logger.info(f"✅ [DB] Logged LP block for {lp}")
        except Exception as e:
            logger.error(f"❌ [DB] Failed to log LP block: {e}")

    def log_interaction(self, speaker: str, action: str, content: str):
        logger.info(f"{speaker.upper()} {action}: {content}")

class AudioCoordinator:
    """Handles TTS coordination with frontend"""
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.pending_questions: Dict[str, Dict] = {}
        self.tts_events: Dict[str, asyncio.Event] = {}

    async def speak_and_wait(self, text: str, speech_type: str = "system") -> None:
        """Generate speech and wait for frontend playback completion"""
        message_id = str(uuid.uuid4())
        
        logger.info(f"🔊 [AUDIO] Generating speech: {text[:50]}... (type: {speech_type})")
        
        # Register for completion tracking
        self.pending_questions[message_id] = {
            "text": text,
            "type": speech_type,
            "status": "generating",
            "timestamp": time.time()
        }
        
        try:
            # Generate audio using TTS service directly (no WebSocket overhead!)
            audio_data = await tts_service.generate_speech(text, speech_type)
            
            if audio_data:
                # Send audio directly to frontend
                import base64
                audio_b64 = base64.b64encode(audio_data).decode('utf-8')
                
                await self.websocket.send_json({
                    "type": "speech",
                    "text": text,
                    "speech_type": speech_type,
                    "message_id": message_id,
                    "audio_data": audio_b64,
                    "format": "mp3",
                    "has_rime_audio": True
                })
                
                # Wait for frontend playback completion
                await self._wait_for_playback_completion(message_id)
            else:
                # Fallback to text-only
                await self.websocket.send_json({
                    "type": "speech",
                    "text": text,
                    "speech_type": speech_type,
                    "message_id": message_id,
                    "has_rime_audio": False
                })
                await asyncio.sleep(2)  # Brief pause for text reading
                
        except Exception as e:
            logger.error(f"❌ [AUDIO] Speech generation failed: {e}")
            # Send text fallback
            try:
                await self.websocket.send_json({
                    "type": "speech",
                    "text": text,
                    "speech_type": speech_type,
                    "message_id": message_id,
                    "error": str(e),
                    "has_rime_audio": False
                })
                await asyncio.sleep(2)
            except:
                pass

    async def get_user_response_only(self, max_tries: int = 2) -> str:
        """Get user response without asking a question (for moderation retries)"""
        logger.info("🎧 [AUDIO] Getting user response without repeating question")
        
        try:
            # Signal frontend to start listening (no question audio)
            await self.websocket.send_json({
                "type": "start_listening"
            })
            
            # Get user response via STT (direct service call!)
            cancel_event = threading.Event()

            async def bridge_cancellation():
                await self.websocket.cancel_event if hasattr(self.websocket, 'cancel_event') else asyncio.Event().wait()
                cancel_event.set()
                
            bridge_task = asyncio.create_task(bridge_cancellation()) if hasattr(self, 'cancel_event') else None
            
            for attempt in range(max_tries):
                logger.info(f"🎧 [STT] Listening for response (attempt {attempt + 1}/{max_tries})")
                
                # Direct STT service call - no WebSocket overhead!
                try: 
                    transcript = await stt_service.transcribe_speech(
                    stop_duration=3,
                    max_wait=60,
                    cancel_event=cancel_event
                )
                finally:
                    if bridge_task:
                        bridge_task.cancel()
                        try:
                            await bridge_task
                        except asyncio.CancelledError:
                            pass
                
                if transcript and transcript.strip():
                    logger.info(f"✅ [STT] Got response: {transcript}")
                    
                    # Send confirmation to frontend
                    await self.websocket.send_json({
                        "type": "answer",
                        "text": transcript
                    })
                    
                    return transcript
                else:
                    if attempt < max_tries - 1:
                        await self.speak_and_wait("Please share your thoughts when you're ready.", "retry")
                        await self.websocket.send_json({"type": "start_listening"})
            
            # Max retries reached
            await self.speak_and_wait("No response detected. Let's move on.", "skip")
            return ""
            
        except Exception as e:
            logger.error(f"❌ [AUDIO] Response-only error: {e}")
            return ""

    async def ask_question_and_get_response(self, question: str, max_tries: int = 2) -> str:
        """Ask question with audio and get user response via STT"""
        message_id = str(uuid.uuid4())
        
        logger.info(f"🎤 [INTERVIEW] Asking question: {question[:50]}...")
        
        try:
            # Generate question audio
            audio_data = await tts_service.generate_speech(question, "question")
            
            if audio_data:
                import base64
                audio_b64 = base64.b64encode(audio_data).decode('utf-8')
                
                await self.websocket.send_json({
                    "type": "question",
                    "text": question,
                    "message_id": message_id,
                    "audio_data": audio_b64,
                    "format": "mp3",
                    "has_rime_audio": True
                })
            else:
                # Text fallback
                await self.websocket.send_json({
                    "type": "question",
                    "text": question,
                    "message_id": message_id,
                    "has_rime_audio": False
                })
            
            # Wait for TTS completion before starting STT
            await self._wait_for_playback_completion(message_id)
            
            # Signal frontend to start listening
            await self.websocket.send_json({
                "type": "start_listening"
            })
            
            # Get user response via STT (direct service call!)
            cancel_event = threading.Event()

            bridge_task = None
            if hasattr(self, 'session_cancel_event'):
                async def bridge_cancellation():
                    await self.session_cancel_event.wait()
                    cancel_event.set()
                    logger.info("🚨 [STT] Session cancelled - stopping STT")
                bridge_task = asyncio.create_task(bridge_cancellation())
            
            for attempt in range(max_tries):
                logger.info(f"🎧 [STT] Listening for response (attempt {attempt + 1}/{max_tries})")
                
                # Direct STT service call - no WebSocket overhead!
                try:
                    transcript = await stt_service.transcribe_speech(
                    stop_duration=3,
                    max_wait=60,
                    cancel_event=cancel_event
                )
                finally:
                    if bridge_task:
                        bridge_task.cancel()
                        try:
                            await bridge_task
                        except asyncio.CancelledError:
                            pass
                
                if transcript and transcript.strip():
                    logger.info(f"✅ [STT] Got response: {transcript}")
                    
                    # Send confirmation to frontend
                    await self.websocket.send_json({
                        "type": "answer",
                        "text": transcript
                    })
                    
                    return transcript
                else:
                    if attempt < max_tries - 1:
                        await self.speak_and_wait("Please share your thoughts when you're ready.", "retry")
                        await self.websocket.send_json({"type": "start_listening"})
            
            # Max retries reached
            await self.speak_and_wait("No response detected. Let's move on.", "skip")
            return ""
            
        except Exception as e:
            logger.error(f"❌ [INTERVIEW] Question/response error: {e}")
            return ""

    async def handle_frontend_message(self, message: dict) -> None:
        """Handle messages from frontend (TTS completion signals, etc.)"""
        msg_type = message.get("type")
        message_id = message.get("message_id")
        
        if msg_type in ["audio_playback_completed", "tts_completed"]:
            await self._handle_playback_completed(message_id, message.get("error"))
        elif msg_type in ["audio_playback_error", "tts_error"]:
            await self._handle_playback_error(message_id, message.get("error"))

    async def _wait_for_playback_completion(self, message_id: str, timeout: int = 30) -> None:
        """Wait for frontend to signal playback completion"""
        event = asyncio.Event()
        self.tts_events[message_id] = event
        
        try:
            await asyncio.wait_for(event.wait(), timeout=timeout)
            logger.info(f"✅ [AUDIO] Playback completed for {message_id}")
        except asyncio.TimeoutError:
            logger.warning(f"⏰ [AUDIO] Playback timeout for {message_id}")
        finally:
            # Cleanup
            if message_id in self.tts_events:
                del self.tts_events[message_id]
            if message_id in self.pending_questions:
                del self.pending_questions[message_id]

    async def _handle_playback_completed(self, message_id: str, error: Optional[str] = None) -> None:
        """Handle playback completion signal"""
        if message_id in self.tts_events:
            if error:
                logger.warning(f"⚠️ [AUDIO] Playback completed with error for {message_id}: {error}")
            else:
                logger.info(f"✅ [AUDIO] Playback completed successfully for {message_id}")
            self.tts_events[message_id].set()

    async def _handle_playback_error(self, message_id: str, error: str) -> None:
        """Handle playback error signal"""
        if message_id in self.tts_events:
            logger.error(f"❌ [AUDIO] Playback error for {message_id}: {error}")
            self.tts_events[message_id].set()

class InterviewSessionService:
    """Main interview session orchestrator - integrates all services"""
    
    def __init__(self, user_id: str, websocket: WebSocket):
        self.user_id = user_id
        self.websocket = websocket
        self.config = InterviewConfig()
        
        # Load interview questions
        import os
        questions_path = os.path.join(os.path.dirname(__file__), "..", "..", "questions.json")
        try:
            with open(questions_path, "r") as f:
                self.lp_questions = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load questions: {e}")
            # Fallback questions
            self.lp_questions = {
                "Customer Obsession": ["Tell me about a time you went above and beyond for a customer."],
                "Ownership": ["Tell me about a time you took ownership of something outside your role."]
            }
        
        # Initialize all components
        self.session_manager = SessionManager()
        self.lp_selector = LPSelector(self.lp_questions)
        self.moderator = ModerationService()
        self.logger = InteractionLogger(user_id)
        self.audio_coordinator = AudioCoordinator(websocket)
        self.cancel_event = asyncio.Event()
        self.audio_coordinator.session_cancel_event = self.cancel_event
        
        # Session state
        self.session_id = self.session_manager.get_session_id()
        self.stats = SessionStats(
            session_id=self.session_id,
            user_id=user_id,
            start_time=datetime.now()
        )

    async def start_interview(self) -> None:
        """Main interview flow orchestrator"""
        logger.info(f"🎭 [SESSION] Starting interview for user {self.user_id}")
        
        try:
            # Send initial message
            await self.websocket.send_json({
                "type": "system",
                "text": "Interview started!",
                "session_id": self.session_id
            })
            
            # Create concurrent tasks
            interview_task = asyncio.create_task(self._run_interview())
            disconnect_task = asyncio.create_task(self._monitor_disconnect())
            message_task = asyncio.create_task(self._listen_for_messages())
            
            # Wait for first completion
            done, pending = await asyncio.wait(
                [interview_task, disconnect_task, message_task],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Cancel remaining tasks
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                    
        except Exception as e:
            logger.error(f"❌ [SESSION] Interview error: {e}")
        finally:
            await self._cleanup_session()

    async def _run_interview(self) -> None:
        """Main interview logic"""
        logger.info("🎯 [INTERVIEW] Starting main interview flow")
        
        self.session_manager.start_session()
        self.stats.status = "active"
        
        # Introduction sequence
        await self._run_intro()
        
        if self.cancel_event.is_set():
            return
        
        # Main interview loop
        lp_asked = 0
        
        while (self.session_manager.time_remaining(self.config.session_duration_limit) > 0 
               and lp_asked < self.config.min_lp_questions 
               and not self.cancel_event.is_set()):
            
            lp = self.lp_selector.pick_new_lp()
            if not lp:
                break
                
            logger.info(f"🎯 [LP] Starting leadership principle: {lp}")
            
            # Get main question
            main_question = random.choice(self.lp_questions[lp])
            
            # Ask main question and handle retries/moderation
            main_answer = await self._ask_question_with_moderation(main_question)
            
            if not main_answer or self.cancel_event.is_set():
                continue
            
            # Handle followups
            followups = await self._handle_followups(lp, main_question, main_answer)
            
            if not self.cancel_event.is_set():
                # Log to database
                self.logger.log_lp_block(self.session_id, lp, main_question, main_answer, followups)
                lp_asked += 1
                self.stats.lp_questions_asked = lp_asked
                
                if lp_asked < self.config.min_lp_questions:
                    await self.audio_coordinator.speak_and_wait(
                        "Thank you for your response. Let's move to the next topic.", 
                        "transition"
                    )
        
        # Complete interview
        if not self.cancel_event.is_set():
            await self.audio_coordinator.speak_and_wait(
                "Thank you for your time. The interview session is now complete.", 
                "completion"
            )
            
            await self.websocket.send_json({
                "type": "complete",
                "session_id": self.session_id
            })
            
            self.stats.status = "completed"
            self.stats.end_time = datetime.now()
            
            # Cleanup session memory
            session_memory_manager.cleanup_session(self.session_id)

    async def _run_intro(self) -> None:
        """Introduction sequence"""
        logger.info("👋 [INTRO] Starting introduction")
        
        if self.cancel_event.is_set():
            return
            
        intro_text = (
            "Hi there! My name is Aron, and I'll be your interviewer today."
        )
        
        user_intro = await self.audio_coordinator.ask_question_and_get_response(intro_text)
        
        if self.cancel_event.is_set():
            return
            
        if user_intro and user_intro.strip():
            await self.audio_coordinator.speak_and_wait(
                "Thanks for the introduction. It's great to learn a bit about you. Let's get started with the interview.",
                "transition"
            )
        else:
            await self.audio_coordinator.speak_and_wait(
                "Let's begin with the interview.",
                "transition"
            )

    async def _ask_question_with_moderation(self, question: str) -> str:
        """Ask question and handle moderation/retries"""
        question_asked = False
        
        while True:
            if self.cancel_event.is_set():
                return ""
            
            # Ask question only if not asked yet, or if repeat was requested
            if not question_asked:
                answer = await self.audio_coordinator.ask_question_and_get_response(question)
                question_asked = True
            else:
                # Just get user response without repeating question
                answer = await self.audio_coordinator.get_user_response_only()
                
            if not answer:
                return ""
                
            # Moderate response using direct service call (no HTTP overhead!)
            mod_result = self.moderator.moderate(question, answer)
            
            if mod_result.status in ["abusive", "malicious"]:
                await self.audio_coordinator.speak_and_wait(
                    "Interview terminated due to inappropriate behavior.", 
                    "termination"
                )
                await self.websocket.send_json({
                    "type": "terminate", 
                    "reason": "inappropriate"
                })
                self.cancel_event.set()
                return ""
                
            elif mod_result.status == "off_topic":
                await self.audio_coordinator.speak_and_wait(
                    "Please try to answer the question related to your experience.", 
                    "moderation"
                )
                continue  # Keep question_asked = True, so won't repeat question
                
            elif mod_result.status == "repeat":
                await self.audio_coordinator.speak_and_wait(
                    "Sure, let me repeat the question.", 
                    "moderation"
                )
                question_asked = False  # Reset flag to repeat question
                continue
                
            elif mod_result.status == "change":
                await self.audio_coordinator.speak_and_wait(
                    "Unfortunately, we can't change the question, but feel free to use any academic, co-curricular, or personal experiences to answer it.", 
                    "moderation"
                )
                continue  # Keep question_asked = True, so won't repeat question
                
            elif mod_result.status == "thinking":
                await self.audio_coordinator.speak_and_wait(
                    "Sure, take your time.", 
                    "moderation"
                )
                continue  # Keep question_asked = True, so won't repeat question
            else:
                return answer  # Valid answer

    async def _handle_followups(self, lp: str, main_question: str, main_answer: str) -> list:
        """Handle followup questions for an LP"""
        followups = []
        current_q, current_a = main_question, main_answer
        num_followups = 0
        
        while (num_followups < self.config.follow_up_count and not self.cancel_event.is_set()):
            
            if self.session_manager.time_remaining(self.config.session_duration_limit) <= 0:
                break
                
            # Check if should generate followup (direct service call!)
            should_generate_req = ShouldGenerateRequest(
                session_id=self.session_id,
                principle=lp,
                question=current_q,
                user_input=current_a,
                time_remaining=int(self.session_manager.time_remaining(self.config.session_duration_limit) / 60),
                time_spent=int(self.session_manager.get_elapsed_time() / 60),
                num_followups=num_followups,
                num_lp_questions=self.stats.lp_questions_asked
            )
            
            should_generate = followup_service.should_generate_followup(should_generate_req)
            
            # if not should_generate:
            #     break
                
            # Generate followup (direct service call!)
            followup_req = FollowupRequest(
                session_id=self.session_id,
                principle=lp,
                question=current_q,
                user_input=current_a
            )
            
            followup_question = followup_service.generate_followup(followup_req)
            
            if self.cancel_event.is_set():
                break
                
            # Ask followup with moderation
            followup_answer = await self._ask_question_with_moderation(followup_question)
            
            if followup_answer and not self.cancel_event.is_set():
                followups.append({
                    "question": followup_question,
                    "answer": followup_answer
                })
                current_q, current_a = followup_question, followup_answer
                num_followups += 1
                self.stats.total_followups += 1
        
        return followups

    async def _listen_for_messages(self) -> None:
        """Listen for messages from frontend"""
        logger.info("👂 [MESSAGES] Starting message listener")
        
        try:
            while not self.cancel_event.is_set():
                message = await self.websocket.receive_json()
                logger.info(f"📨 [MESSAGE] Received: {message.get('type')}")
                
                # Handle audio coordination messages
                await self.audio_coordinator.handle_frontend_message(message)
                
                # Handle session control messages
                if message.get("type") == "end_session":
                    logger.info("🛑 [SESSION] End session command received")
                    self.cancel_event.set()
                    break
                    
        except WebSocketDisconnect:
            logger.info("🔌 [MESSAGES] WebSocket disconnected")
            self.cancel_event.set()
        except Exception as e:
            logger.error(f"❌ [MESSAGES] Message listener error: {e}")
            self.cancel_event.set()

    async def _monitor_disconnect(self) -> None:
        """Monitor WebSocket disconnection"""
        logger.info("🔍 [MONITOR] Starting disconnect monitoring")
        
        while not self.cancel_event.is_set():
            try:
                # Send heartbeat
                await self.websocket.send_json({
                    "type": "heartbeat",
                    "timestamp": time.time()
                })
                await asyncio.sleep(5.0)  # Check every 5 seconds
                
            except Exception as e:
                logger.info(f"🔌 [MONITOR] WebSocket disconnected: {e}")
                self.cancel_event.set()
                break

    async def _cleanup_session(self) -> None:
        """Cleanup session resources"""
        logger.info(f"🧹 [CLEANUP] Cleaning up session {self.session_id}")
        
        try:
            # Update final stats
            if self.stats.end_time is None:
                self.stats.end_time = datetime.now()
                self.stats.status = "terminated"
            
            # Cleanup session memory
            session_memory_manager.cleanup_session(self.session_id)
            
            logger.info(f"✅ [CLEANUP] Session cleanup completed for {self.session_id}")
            
        except Exception as e:
            logger.error(f"❌ [CLEANUP] Cleanup error: {e}")

# Global active sessions tracking for deduplication
active_sessions: Set[str] = set()