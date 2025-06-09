import requests
import logging
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from config.constants import LLM_ENDPOINT

class FollowupManager:
    def __init__(self, tts, session_id):
        self.tts = tts
        self.session_id = session_id

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
            logging.error(f"\u274c Error calling LLM microservice: {e}")
            self.tts.speak("Can you elaborate further on that?")
            return "Can you elaborate further on that?"