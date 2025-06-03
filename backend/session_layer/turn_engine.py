import json
import random
import time

import sys
import os

# Ensure both layers are importable
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "interaction_layer"))

from stt_handler import transcribe_speech
from mock_llm import generate_response
from tts_handler import TTSHandler

# Constants
SESSION_DURATION_LIMIT = 5 * 60  # in seconds
MIN_LP_QUESTIONS = 3
FOLLOW_UP_COUNT = 3

class TurnEngine:
    def __init__(self):
        question_file = os.path.join(os.path.dirname(__file__), "questions.json")
        with open(question_file, "r") as f:
            self.lp_questions = json.load(f)

        self.asked_principles = set()
        self.session_start_time = None
        self.tts = TTSHandler()

    def time_remaining(self):
        return SESSION_DURATION_LIMIT - (time.time() - self.session_start_time)

    def pick_new_lp(self):
        remaining = list(set(self.lp_questions.keys()) - self.asked_principles)
        if not remaining:
            return None
        return random.choice(remaining)

    def ask_question(self, text):
        print("Bot:", text)
        self.tts.speak(text)

    def start_interview(self):
        print("Interview started. Maximum duration: 60 minutes.")
        self.session_start_time = time.time()
        lp_asked = 0

        while self.time_remaining() > 0 and lp_asked < MIN_LP_QUESTIONS:
            lp = self.pick_new_lp()
            if not lp:
                break  # All LPs exhausted

            self.asked_principles.add(lp)
            lp_questions = self.lp_questions[lp]
            main_question = random.choice(lp_questions)
            print(f"\n[Leadership Principle: {lp}]")

            # Ask main question
            self.ask_question(main_question)
            user_answer = transcribe_speech()

            # Follow-up loop
            followup_prompt = f"The user said: '{user_answer}'. Ask a follow-up question to go deeper on the topic."
            for _ in range(FOLLOW_UP_COUNT):
                if self.time_remaining() <= 0:
                    break
                follow_up = generate_response(followup_prompt)
                self.ask_question(follow_up)
                user_answer = transcribe_speech()
                followup_prompt = f"The user said: '{user_answer}'. Ask another follow-up question."

            lp_asked += 1

        print("\n✅ Interview session complete. Thank you!")
        self.tts.speak("Your mock interview session is now complete. Thank you!")


if __name__ == "__main__":
    engine = TurnEngine()
    engine.start_interview() 