import requests
import logging
import sys, os
from datetime import datetime
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config.constants import LLM_ENDPOINT, SHOULD_GENERATE_ENDPOINT
from utils.stream_buffer import StreamTextChunkBuffer

class FollowupManager:
    def __init__(self, tts, session_id):
        self.tts = tts
        self.session_id = session_id
        self.start_time = datetime.now()

    def _time_elapsed(self):
        seconds = (datetime.now() - self.start_time).total_seconds()
        return round(seconds / 60)

    def should_generate_followup(self, principle, question, user_input, num_followups, num_lp_questions, time_remaining):
        payload = {
            "session_id": self.session_id,
            "principle": principle,
            "question": question,
            "user_input": user_input,
            "time_remaining": time_remaining,
            "time_spent": self._time_elapsed(),
            "num_followups": num_followups,
            "num_lp_questions": num_lp_questions
        }
        logging.info(f"Checking if should generate follow-up | Session ID: {self.session_id}, LP: {principle}, Q: {question}, A: {user_input}, Time Remaining: {time_remaining}, Time Spent: {self._time_elapsed()}, Num Followups: {num_followups}, Num LP Questions: {num_lp_questions}")
        try:
            resp = requests.post(SHOULD_GENERATE_ENDPOINT, json=payload)
            resp.raise_for_status()
            result = resp.json()
            return result.get("followup", True)  # default to True if not specified

        except requests.RequestException as e:
            logging.warning(f"⚠️ Could not reach should_generate_followup endpoint: {e}")
            return True  # default: try generating

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

            buffer_manager = StreamTextChunkBuffer(tts=self.tts)
            followup_parts = []

            for chunk in response.iter_content(chunk_size=64, decode_unicode=True):
                if not chunk.strip():
                    continue
                buffer_manager.feed_chunk(chunk)
                followup_parts.append(chunk)

            buffer_manager.flush()

            followup = "".join(followup_parts).strip()
            logging.info(f"LLM Follow-up (final): {followup}")
            return followup

        except requests.exceptions.RequestException as e:
            logging.error(f"❌ Error calling LLM microservice: {e}")
            self.tts.speak("Can you elaborate further on that?")
            return "Can you elaborate further on that?"
