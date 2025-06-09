import logging
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from services.stt_handler import transcribe_speech

class QuestionHandler:
    def __init__(self, tts, session_timer, session_limit):
        self.tts = tts
        self.session_timer = session_timer
        self.session_limit = session_limit

    def ask_question(self, text):
        print("Bot:", text)
        logging.info(f"Bot asked: {text}")
        self.tts.speak(text)

    def wait_for_user_response(self, question, max_tries=2):
        print("Waiting for user to speak...")

        for attempt in range(max_tries):
            if self.session_timer.time_remaining(self.session_limit) <= 0:
                break

            transcript = transcribe_speech(stop_duration=4.0, max_wait=10)
            if transcript.strip():
                return transcript

            if attempt < max_tries - 1:
                logging.info(f"User did not respond. Attempt {attempt + 1} of {max_tries - 1}.")
                self.tts.speak("Please share your thoughts when you're ready.")

        return ""