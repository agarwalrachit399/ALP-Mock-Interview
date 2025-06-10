
import json
import logging
import random
import sys
import os
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
from config.constants import SESSION_DURATION_LIMIT, MIN_LP_QUESTIONS, FOLLOW_UP_COUNT, QUESTION_FILE
from session_manager import SessionManager
from lp_selector import LPSelector
from services.moderation_service import ModerationService
from services.followup_manager import FollowupManager
from handlers.question_handler import QuestionHandler
from custom_logging.logger import InteractionLogger
from services.tts_handler import TTSHandler


log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

file_handler = logging.FileHandler("interview_log.txt", mode="a")
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(log_formatter)

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)

class TurnEngine:
    def __init__(self):
        with open(QUESTION_FILE, "r") as f:
            self.lp_questions = json.load(f)

        self.session_manager = SessionManager()
        self.tts = TTSHandler()
        self.lp_selector = LPSelector(self.lp_questions)
        self.moderator = ModerationService()
        self.logger = InteractionLogger()
        self.question_handler = QuestionHandler(self.tts, self.session_manager, SESSION_DURATION_LIMIT)

    def start_interview(self):
        print("Interview started. Maximum duration: 60 minutes.")
        logging.info("Interview session started")

        self.session_manager.start_session()
        session_id = self.session_manager.get_session_id()
        followup_manager = FollowupManager(self.tts, session_id)
        lp_asked = 0

        while self.session_manager.time_remaining(SESSION_DURATION_LIMIT) > 0 and lp_asked < MIN_LP_QUESTIONS:
            lp = self.lp_selector.pick_new_lp()
            if not lp:
                break

            main_question = random.choice(self.lp_questions[lp])
            print(f"\n[Leadership Principle: {lp}]")
            logging.info(f"Starting LP block: {lp}")

            self.question_handler.ask_question(main_question)

            while True:
                main_answer = self.question_handler.wait_for_user_response(main_question)
                if not main_answer.strip():
                    logging.info("Moving to next question due to empty response.")
                    self.tts.speak("Moving to next question due to empty response.")
                    break

                mod_status = self.moderator.moderate(main_question, main_answer)
                logging.info(f"Moderation status: {mod_status}")

                if mod_status in ["abusive", "malicious"]:
                    self.tts.speak("Interview terminated due to inappropriate content.")
                    return
                elif mod_status == "off_topic":
                    self.tts.speak("Please try to answer the question related to your experience.")
                elif mod_status == "repeat":
                    self.tts.speak("Sure, let me repeat the question.")
                    self.question_handler.ask_question(main_question)
                elif mod_status == "change":
                    self.tts.speak("Unfortunately, we can't change the question, but feel free to use any academic, co-curricular, or personal experiences to answer it.")
                elif mod_status == "thinking":
                    self.tts.speak("Sure, take a couple of minutes.")
                else:
                    break

            if not main_answer.strip():
                continue

            followups = []
            current_q = main_question
            current_a = main_answer

            num_followups = 0
            while num_followups < FOLLOW_UP_COUNT:
                if self.session_manager.time_remaining(SESSION_DURATION_LIMIT) <= 0:
                    break

                should_generate = followup_manager.should_generate_followup(
                    lp,
                    current_q,
                    current_a,
                    num_followups,
                    lp_asked,
                    round(self.session_manager.time_remaining(SESSION_DURATION_LIMIT) / 60)

                )

                if not should_generate:
                    logging.info(f"Follow-up skipped by policy after {num_followups} follow-up(s).")
                    break

                follow_up = followup_manager.generate_followup(lp, current_q, current_a)

                while True:
                    user_answer = self.question_handler.wait_for_user_response(follow_up)
                    mod_status = self.moderator.moderate(follow_up, user_answer)

                    if mod_status in ["abusive", "malicious"]:
                        self.tts.speak("Interview terminated due to inappropriate content.")
                        return
                    elif mod_status == "off_topic":
                        self.tts.speak("Please answer the question based on your relevant experience.")
                    elif mod_status == "repeat":
                        self.tts.speak("Sure, let me repeat the question.")
                        self.question_handler.ask_question(follow_up)
                    elif mod_status == "change":
                        self.tts.speak("Unfortunately, we can't change the question, but feel free to use any academic, co-curricular, or personal experiences to answer it.")
                    elif mod_status == "thinking":
                        self.tts.speak("Sure, take your time.")
                    else:
                        break

                followups.append({"question": follow_up, "answer": user_answer})
                current_q, current_a = follow_up, user_answer
                num_followups += 1


            self.logger.log_lp_block(session_id, lp, main_question, main_answer, followups)
            lp_asked += 1

        self.tts.speak("Your mock interview session is now complete. Thank you!")
        print("\n✅ Interview session complete. Thank you!")
        logging.info("Interview session completed")


if __name__ == "__main__":
    engine = TurnEngine()
    engine.start_interview()
