import logging
import random
import json
import os
from datetime import datetime

from session_engine.config.constants import SESSION_DURATION_LIMIT, MIN_LP_QUESTIONS, FOLLOW_UP_COUNT, QUESTION_FILE
from session_engine.engine.session_manager import SessionManager
from session_engine.engine.lp_selector import LPSelector
from session_engine.services.moderation_service import ModerationService
from session_engine.services.followup_manager import FollowupManager
from session_engine.custom_logging.logger import InteractionLogger
from session_engine.handlers.ws_question_handler import WebSocketQuestionHandler
from session_engine.services.tts_handler import TTSHandler


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
        self.question_handler = WebSocketQuestionHandler(websocket, tts_handler)
        self.session_id = None

    async def start(self):
        logging.info("WebSocket interview session started")
        await self.websocket.send_json({"type": "system", "text": "Interview started!"})

        self.session_manager.start_session()
        self.session_id = self.session_manager.get_session_id()
        followup_manager = FollowupManager(self.tts, self.session_id)

        lp_asked = 0

        while self.session_manager.time_remaining(SESSION_DURATION_LIMIT) > 0 and lp_asked < MIN_LP_QUESTIONS:
            lp = self.lp_selector.pick_new_lp()
            if not lp:
                break

            main_question = random.choice(self.lp_questions[lp])
            await self.question_handler.ask_question(main_question)

            while True:
                main_answer = await self.question_handler.get_user_response()
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

            if not main_answer:
                continue

            followups = []
            current_q, current_a = main_question, main_answer
            num_followups = 0

            while num_followups < FOLLOW_UP_COUNT:
                if self.session_manager.time_remaining(SESSION_DURATION_LIMIT) <= 0:
                    break

                should_generate = followup_manager.should_generate_followup(
                    lp, current_q, current_a, num_followups, lp_asked,
                    round(self.session_manager.time_remaining(SESSION_DURATION_LIMIT) / 60)
                )

                if not should_generate:
                    break

                follow_up = followup_manager.generate_followup(lp, current_q, current_a)
                await self.websocket.send_json({
                    "type": "question",
                    "text": follow_up
                })


                while True:
                    user_answer = await self.question_handler.get_user_response()
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

                followups.append({"question": follow_up, "answer": user_answer})
                current_q, current_a = follow_up, user_answer
                num_followups += 1

            self.logger.log_lp_block(self.session_id, lp, main_question, main_answer, followups)
            lp_asked += 1

        await self.websocket.send_json({"type": "complete", "text": "Interview session complete!"})
        logging.info("WebSocket interview session completed")
