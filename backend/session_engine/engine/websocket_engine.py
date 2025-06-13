import logging
import random
import json
import os
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
        """Listen for messages from frontend (like end command)"""
        print("🔍 [DEBUG] Starting message listener")
        try:
            while not self.cancel_event.is_set():
                message = await self.websocket.receive_json()
                print(f"🔍 [DEBUG] Received message from frontend: {message}")
                
                if message.get("type") == "end_session":
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
        """Main interview loop - moved from start() method"""
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
                
            await self.question_handler.ask_question(main_question)

            while True:
                main_answer = await self.question_handler.get_user_response()
                
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
                    self.tts.speak("Please try to answer the question related to your experience.")
                elif mod_status == "repeat":
                    self.tts.speak("Sure, let me repeat the question.")
                    await self.question_handler.ask_question(main_question)
                elif mod_status == "change":
                    self.tts.speak("Unfortunately, we can't change the question, but feel free to use any academic, co-curricular, or personal experiences to answer it.")
                elif mod_status == "thinking":
                    self.tts.speak("Sure, take a couple of minutes.")
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
                    
                await self.websocket.send_json({
                    "type": "question",
                    "text": follow_up
                })

                while True:
                    user_answer = await self.question_handler.get_user_response()
                    
                    if self.cancel_event.is_set():
                        return
                        
                    if not user_answer:
                        break

                    mod_status = self.moderator.moderate(follow_up, user_answer)

                    if mod_status in ["abusive", "malicious"]:
                        await self.websocket.send_json({"type": "terminate", "reason": "inappropriate"})
                        return
                    elif mod_status == "off_topic":
                        self.tts.speak("Please answer the question based on your relevant experience.")
                    elif mod_status == "repeat":
                        self.tts.speak("Sure, let me repeat the question.")
                        await self.question_handler.ask_question(follow_up)
                    elif mod_status == "change":
                        self.tts.speak("Unfortunately, we can't change the question, but feel free to use any academic, co-curricular, or personal experiences to answer it.")
                    elif mod_status == "thinking":
                        self.tts.speak("Sure, take your time.")
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
                    self.tts.speak(f"Thank you for your response. Let's move to the next topic.")

        # Only send completion message if not cancelled
        if not self.cancel_event.is_set():
            self.tts.speak("Thank you for your time. The interview session is now complete.")
            await self.websocket.send_json({"type": "complete", "text": "Interview session complete!","session_id": self.session_id })
        
        logging.info("Interview loop completed")
