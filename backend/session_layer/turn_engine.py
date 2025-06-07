import json
import random
import time
import sys
import os
import requests
import logging
import uuid

# Setup logging
logging.basicConfig(
    filename="interview_log.txt",
    filemode="a",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Ensure both layers are importable
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "interaction_layer"))
from stt_handler import transcribe_speech
from tts_handler import TTSHandler
from db_handler import MongoLogger

# Constants
SESSION_DURATION_LIMIT = 5 * 60  # in seconds
MIN_LP_QUESTIONS = 1
FOLLOW_UP_COUNT = 1
LLM_ENDPOINT = "http://localhost:8000/generate-followup"  # Adjust if needed
MODERATION_ENDPOINT = "http://localhost:8100/moderate"

class TurnEngine:
    def __init__(self):
        question_file = os.path.join(os.path.dirname(__file__), "questions.json")
        with open(question_file, "r") as f:
            self.lp_questions = json.load(f)

        self.asked_principles = set()
        self.session_start_time = None
        self.session_id = str(uuid.uuid4())
        self.tts = TTSHandler()
        self.db_logger = MongoLogger()

    def time_remaining(self):
        return SESSION_DURATION_LIMIT - (time.time() - self.session_start_time)

    def pick_new_lp(self):
        remaining = list(set(self.lp_questions.keys()) - self.asked_principles)
        if not remaining:
            return None
        return random.choice(remaining)

    def ask_question(self, text):
        print("Bot:", text)
        logging.info(f"Bot asked: {text}")
        self.tts.speak(text)

    def moderate_input(self, question, user_input):
        try:
            payload = {"question": question, "user_input": user_input}
            response = requests.post(MODERATION_ENDPOINT, json=payload)
            response.raise_for_status()
            return response.json().get("status", "safe")
        except requests.exceptions.RequestException as e:
            logging.error(f"Moderation error: {e}")
            return "safe"

    def generate_followup(self, principle, question, user_input):
        payload = {
            "session_id": self.session_id,
            "principle": principle,
            "question": question,
            "user_input": user_input
        }

        logging.info(f"Generating follow-up (streaming) | Session ID: {self.session_id}, LP: {principle}, Q: {question}, A: {user_input}")
        
        try:
            response = requests.post(LLM_ENDPOINT, json=payload, stream=True)
            response.raise_for_status()

            followup_parts = []
            buffer = ""
            last_chunk = ""

            for chunk in response.iter_content(chunk_size=64, decode_unicode=True):
                if not chunk.strip():
                    continue

                # Fix 1: Add a space if needed between chunks
                if last_chunk and not last_chunk[-1].isspace() and not chunk[0].isspace():
                    chunk = " " + chunk

                followup_parts.append(chunk)
                buffer += chunk
                last_chunk = chunk

                if any(p in buffer for p in [".", "?", "!"]) and len(buffer) > 20:
                    self.tts.speak(buffer.strip())
                    buffer = ""

            if buffer.strip():
                self.tts.speak(buffer.strip())

            followup = "".join(followup_parts).strip()
            logging.info(f"LLM Follow-up (final): {followup}")
            return followup

        except requests.exceptions.RequestException as e:
            logging.error(f"❌ Error calling LLM microservice: {e}")
            self.tts.speak("Can you elaborate further on that?")
            return "Can you elaborate further on that?"


    def start_interview(self):
        print("Interview started. Maximum duration: 60 minutes.")
        logging.info("Interview session started")
        self.session_start_time = time.time()
        lp_asked = 0

        while self.time_remaining() > 0 and lp_asked < MIN_LP_QUESTIONS:
            lp = self.pick_new_lp()
            if not lp:
                break

            self.asked_principles.add(lp)
            lp_questions = self.lp_questions[lp]
            main_question = random.choice(lp_questions)

            print(f"\n[Leadership Principle: {lp}]")
            logging.info(f"Starting LP block: {lp}")

            self.ask_question(main_question)

            while True:
                main_answer = transcribe_speech()
                moderation_status = self.moderate_input(main_question, main_answer)
                logging.info(f"Moderation status: {moderation_status}")

                if moderation_status == "abusive" or moderation_status == "malicious":
                    self.tts.speak("Interview terminated due to inappropriate content.")
                    logging.warning("Interview terminated due to abusive input.")
                    return
                elif moderation_status == "off_topic":
                    self.tts.speak("Please try to answer the question related to your experience.")
                else:
                    break

            followup_questions = []
            followup_answers = []
            current_question = main_question
            current_answer = main_answer

            for i in range(FOLLOW_UP_COUNT):
                if self.time_remaining() <= 0:
                    break

                follow_up = self.generate_followup(
                    principle=lp,
                    question=current_question,
                    user_input=current_answer
                )

                while True:
                    user_answer = transcribe_speech()
                    moderation_status = self.moderate_input(follow_up, user_answer)
                    logging.info(f"Moderation status (follow-up {i+1}): {moderation_status}")

                    if moderation_status == "abusive" or moderation_status == "malicious":
                        self.tts.speak("Interview terminated due to inappropriate content.")
                        logging.warning("Interview terminated due to abusive input.")
                        return
                    elif moderation_status == "off_topic":
                        self.tts.speak("Please answer the question based on your relevant experience.")
                    else:
                        break

                followup_questions.append(follow_up)
                followup_answers.append(user_answer)

                current_question = follow_up
                current_answer = user_answer

            followups_data = [
                {"question": q, "answer": a} for q, a in zip(followup_questions, followup_answers)
            ]
            self.db_logger.log_lp_block(self.session_id, lp, main_question, main_answer, followups_data)

            lp_asked += 1

        print("\n✅ Interview session complete. Thank you!")
        logging.info("Interview session completed")
        self.tts.speak("Your mock interview session is now complete. Thank you!")


if __name__ == "__main__":
    engine = TurnEngine()
    engine.start_interview()