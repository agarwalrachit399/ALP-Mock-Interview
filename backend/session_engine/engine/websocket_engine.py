import logging
import random
import json
import os
import uuid
from datetime import datetime
import asyncio
from starlette.websockets import WebSocketState, WebSocketDisconnect
from session_engine.config.constants import SESSION_DURATION_LIMIT, MIN_LP_QUESTIONS, FOLLOW_UP_COUNT, QUESTION_FILE
from session_engine.engine.session_manager import SessionManager
from session_engine.engine.lp_selector import LPSelector
from session_engine.services.moderation_service import ModerationService
from session_engine.services.followup_manager import FollowupManager
from session_engine.custom_logging.logger import InteractionLogger
from session_engine.handlers.ws_question_handler import WebSocketQuestionHandler
from session_engine.services.tts_handler import TTSHandler
import time

class WebSocketInterviewSession:
    def __init__(self, user_id: str, websocket, tts_handler: TTSHandler):
        self.user_id = user_id
        self.websocket = websocket
        self.tts = tts_handler
        with open(QUESTION_FILE, "r") as f:
            self.lp_questions = json.load(f)

        self.session_manager = SessionManager()
        self.lp_selector = LPSelector(self.lp_questions)
        self.moderator = ModerationService()
        self.logger = InteractionLogger(user_id)
        self.cancel_event = asyncio.Event()
        self.question_handler = WebSocketQuestionHandler(websocket, tts_handler, self.cancel_event)
        self.session_id = None
        
        # TTS Coordination State
        self.pending_questions = {}  # Track TTS completion for questions
        self.tts_events = {}  # Store asyncio events for TTS completion
        
    async def start(self):
        logging.info("WebSocket interview session started")
        await self.websocket.send_json({"type": "system", "text": "Interview started!", "session_id": self.session_manager.get_session_id()})

        # Create concurrent tasks including a message listener
        interview_task = asyncio.create_task(self._run_interview())
        disconnect_task = asyncio.create_task(self._monitor_disconnect())
        message_task = asyncio.create_task(self._listen_for_messages())

        try:
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
            logging.error(f"Session error: {e}")
        finally:
            logging.info("WebSocket interview session ended")

    async def _listen_for_messages(self):
        """Listen for messages from frontend (like end command and TTS signals)"""
        print("🔍 [DEBUG] Starting message listener")
        try:
            while not self.cancel_event.is_set():
                message = await self.websocket.receive_json()
                print(f"🔍 [DEBUG] Received message from frontend: {message}")
                
                # Handle TTS coordination messages
                if message.get("type") == "tts_started":
                    await self._handle_tts_started(message)
                elif message.get("type") == "tts_completed":
                    await self._handle_tts_completed(message)
                elif message.get("type") == "end_session":
                    print("🚨 [DEBUG] End session command received from frontend!")
                    print("🚨 [DEBUG] Setting cancel event from message listener")
                    self.cancel_event.set()
                    print(f"🚨 [DEBUG] Cancel event set - is_set(): {self.cancel_event.is_set()}")
                    break
                    
        except WebSocketDisconnect:
            print("🔍 [DEBUG] WebSocket disconnected in message listener")
            self.cancel_event.set()
        except Exception as e:
            print(f"🔍 [DEBUG] Message listener error: {type(e).__name__}: {e}")
            self.cancel_event.set()
        
        print("🔍 [DEBUG] Message listener ended")

    async def _handle_tts_started(self, message):
        """Handle TTS started signal from frontend"""
        message_id = message.get("message_id")
        if message_id and message_id in self.pending_questions:
            self.pending_questions[message_id]["status"] = "tts_active"
            print(f"🔊 [TTS] TTS started for message {message_id}")

    async def _handle_tts_completed(self, message):
        """Handle TTS completion signal from frontend"""
        message_id = message.get("message_id")
        error = message.get("error")
        
        if message_id and message_id in self.pending_questions:
            self.pending_questions[message_id]["status"] = "tts_completed"
            
            if error:
                print(f"🚨 [TTS] TTS error for message {message_id}: {error}")
            else:
                print(f"✅ [TTS] TTS completed for message {message_id}")
            
            # Signal waiting coroutine
            if message_id in self.tts_events:
                self.tts_events[message_id].set()

    async def _wait_for_tts_completion(self, message_id, timeout=10):
        """Wait for TTS completion signal with timeout"""
        if message_id not in self.pending_questions:
            print(f"⚠️ [TTS] Message {message_id} not in pending questions")
            return
        
        # Create event for this message
        event = asyncio.Event()
        self.tts_events[message_id] = event
        
        try:
            print(f"⏳ [TTS] Waiting for TTS completion of message {message_id} (timeout: {timeout}s)")
            await asyncio.wait_for(event.wait(), timeout=timeout)
            print(f"✅ [TTS] TTS completion confirmed for message {message_id}")
        except asyncio.TimeoutError:
            print(f"⏰ [TTS] TTS completion timeout for message {message_id} - proceeding anyway")
            logging.warning(f"TTS completion timeout for {message_id}")
        finally:
            # Cleanup
            if message_id in self.tts_events:
                del self.tts_events[message_id]
            if message_id in self.pending_questions:
                del self.pending_questions[message_id]

    async def speak_and_wait(self, text, speech_type="system"):
        """Send speech message to frontend and wait for TTS completion"""
        message_id = str(uuid.uuid4())
        
        print(f"🔊 [SPEECH] Sending {speech_type} speech: {text[:50]}...")
        
        # Register for TTS tracking
        self.pending_questions[message_id] = {
            "text": text,
            "type": speech_type,
            "status": "tts_pending",
            "timestamp": time.time()
        }
        
        # Send to frontend
        await self.websocket.send_json({
            "type": "speech",
            "text": text,
            "speech_type": speech_type,
            "message_id": message_id
        })
        
        # Wait for completion
        await self._wait_for_tts_completion(message_id, timeout=10)

    async def ask_question_and_wait_for_response(self, question):
        """Ask question with TTS coordination and get response"""
        message_id = str(uuid.uuid4())
        
        print(f"🎤 [INTERVIEW] Asking question with coordination: {question[:50]}...")
        
        # Register question for TTS tracking
        self.pending_questions[message_id] = {
            "question": question,
            "status": "tts_pending",
            "timestamp": time.time()
        }
        
        # Send question with tracking ID
        await self.websocket.send_json({
            "type": "question",
            "text": question,
            "message_id": message_id
        })
        
        # Wait for TTS completion signal from frontend
        await self._wait_for_tts_completion(message_id, timeout=10)
        
        # Only now signal frontend it's safe to start listening
        await self.websocket.send_json({
            "type": "start_listening"
        })
        
        print("🎧 [INTERVIEW] TTS completed, now getting user response...")
        
        # Get user response via STT
        return await self.question_handler.get_user_response()

    async def _monitor_disconnect(self):
        """Monitor WebSocket state and set cancel event when disconnected"""
        print("🔍 [DEBUG] Starting WebSocket disconnect monitoring")
        while not self.cancel_event.is_set():
            try:
                print("🔍 [DEBUG] Sending heartbeat...")
                # Try to send a heartbeat message
                await self.websocket.send_json({
                    "type": "heartbeat",
                    "timestamp": time.time()
                })
                print("🔍 [DEBUG] WebSocket heartbeat sent successfully")
                await asyncio.sleep(2.0)  # Check every 2 seconds
                
            except Exception as e:
                print(f"🚨 [DEBUG] WebSocket disconnected detected: {type(e).__name__}: {e}")
                print("🚨 [DEBUG] SETTING CANCEL EVENT NOW!")
                self.cancel_event.set()
                print(f"🚨 [DEBUG] Cancel event set - is_set(): {self.cancel_event.is_set()}")
                break
                
        print("🔍 [DEBUG] Monitor disconnect loop ended")

    async def _run_interview(self):
        """Main interview loop with TTS coordination"""
        print("🔍 [DEBUG] Starting interview loop")
        self.session_manager.start_session()
        self.session_id = self.session_manager.get_session_id()
        followup_manager = FollowupManager(self.tts, self.session_id)

        lp_asked = 0

        while (self.session_manager.time_remaining(SESSION_DURATION_LIMIT) > 0 
               and lp_asked < MIN_LP_QUESTIONS 
               and not self.cancel_event.is_set()):
            
            print(f"🔍 [DEBUG] Interview loop iteration - cancel_event.is_set(): {self.cancel_event.is_set()}")
            
            lp = self.lp_selector.pick_new_lp()
            if not lp:
                break

            main_question = random.choice(self.lp_questions[lp])
            
            # Check for cancellation before asking question
            if self.cancel_event.is_set():
                break
            
            # Use coordinated question asking
            while True:
                main_answer = await self.ask_question_and_wait_for_response(main_question)
                
                # Check if cancelled during response
                if self.cancel_event.is_set():
                    return
                    
                if not main_answer:
                    await self.websocket.send_json({"type": "system", "text": "No answer. Skipping."})
                    break

                mod_status = self.moderator.moderate(main_question, main_answer)

                if mod_status in ["abusive", "malicious"]:
                    await self.websocket.send_json({"type": "terminate", "reason": "inappropriate"})
                    return
                elif mod_status == "off_topic":
                    await self.speak_and_wait("Please try to answer the question related to your experience.", "moderation")
                elif mod_status == "repeat":
                    await self.speak_and_wait("Sure, let me repeat the question.", "moderation")
                    # Continue loop to ask question again
                elif mod_status == "change":
                    await self.speak_and_wait("Unfortunately, we can't change the question, but feel free to use any academic, co-curricular, or personal experiences to answer it.", "moderation")
                elif mod_status == "thinking":
                    await self.speak_and_wait("Sure, take a couple of minutes.", "moderation")
                else:
                    break

            if not main_answer or self.cancel_event.is_set():
                continue

            followups = []
            current_q, current_a = main_question, main_answer
            num_followups = 0

            while (num_followups < FOLLOW_UP_COUNT 
                   and not self.cancel_event.is_set()):
                   
                if self.session_manager.time_remaining(SESSION_DURATION_LIMIT) <= 0:
                    break

                should_generate = followup_manager.should_generate_followup(
                    lp, current_q, current_a, num_followups, lp_asked,
                    round(self.session_manager.time_remaining(SESSION_DURATION_LIMIT) / 60)
                )

                if not should_generate:
                    break

                follow_up = followup_manager.generate_followup(lp, current_q, current_a)
                
                if self.cancel_event.is_set():
                    break
                
                # Use coordinated question asking for follow-ups too
                while True:
                    user_answer = await self.ask_question_and_wait_for_response(follow_up)
                    
                    if self.cancel_event.is_set():
                        return
                        
                    if not user_answer:
                        break

                    mod_status = self.moderator.moderate(follow_up, user_answer)

                    if mod_status in ["abusive", "malicious"]:
                        await self.websocket.send_json({"type": "terminate", "reason": "inappropriate"})
                        return
                    elif mod_status == "off_topic":
                        await self.speak_and_wait("Please answer the question based on your relevant experience.", "moderation")
                    elif mod_status == "repeat":
                        await self.speak_and_wait("Sure, let me repeat the question.", "moderation")
                        # Continue loop to ask question again
                    elif mod_status == "change":
                        await self.speak_and_wait("Unfortunately, we can't change the question, but feel free to use any academic, co-curricular, or personal experiences to answer it.", "moderation")
                    elif mod_status == "thinking":
                        await self.speak_and_wait("Sure, take your time.", "moderation")
                    else:
                        break

                if user_answer and not self.cancel_event.is_set():
                    followups.append({"question": follow_up, "answer": user_answer})
                    current_q, current_a = follow_up, user_answer
                    num_followups += 1

            if not self.cancel_event.is_set():
                self.logger.log_lp_block(self.session_id, lp, main_question, main_answer, followups)
                lp_asked += 1
                if lp_asked < MIN_LP_QUESTIONS:
                    await self.speak_and_wait(f"Thank you for your response. Let's move to the next topic.", "transition")

        # Only send completion message if not cancelled
        if not self.cancel_event.is_set():
            await self.websocket.send_json({"type": "complete", "text": "Thank you for your time. The interview session is now complete.","session_id": self.session_id })
        
        logging.info("Interview loop completed")