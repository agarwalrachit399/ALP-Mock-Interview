import time
import sys
import os
import logging
import re
import spacy

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "interaction_layer"))
from stt_handler import transcribe_speech
from tts_handler import TTSHandler




class IntroHandler:
    def __init__(self):
        self.tts = TTSHandler()
        self.nlp = spacy.load("en_core_web_sm")

    def extract_name(self, text):
        doc = self.nlp(text)
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                return ent.text
        patterns = [
            r"i['\s]?m\s+([A-Z][a-z]+)",  # I'm Manasi
            r"my name is\s+([A-Z][a-z]+)",  # my name is Manasi
            r"this is\s+([A-Z][a-z]+)",     # this is Manasi
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    def run_intro(self):
        intro_lines = [
            "Hi there! My name is Alex, and I'll be your interviewer today.",
            "I've worked across multiple teams at Amazon and currently lead technical initiatives at AWS.",
            "In today's interview, I'll be asking you behavioral questions based on Amazon's leadership principles.",
            "Each question may be followed by one or two follow-ups depending on your responses.",
            "Please take your time, think through your answers, and try to structure them using the STAR format.",
            "To begin, could you briefly introduce yourself in two to three lines?"
        ]

        for line in intro_lines:
            print("Bot:", line)
            logging.info(f"[Intro] Bot: {line}")
            self.tts.speak(line)
            time.sleep(0.2)

        user_intro = transcribe_speech()
        logging.info(f"[Intro] User Introduction: {user_intro}")
        print("User:", user_intro)

        name = self.extract_name(user_intro)
        print(name)

        if name:
            closing_line = f"Thanks for the introduction, {name}. Let's get started with the interview."
        else:
            closing_line = "Thanks for the introduction. It’s great to learn a bit about you. Let’s get started with the interview."

        print("Bot:", closing_line)
        self.tts.speak(closing_line)

        return user_intro
