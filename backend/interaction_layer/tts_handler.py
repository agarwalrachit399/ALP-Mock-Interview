from RealtimeTTS import ElevenlabsEngine, TextToAudioStream
import os
from dotenv import load_dotenv

load_dotenv()

ELVEN_LAB_API_KEY = os.getenv('ELVENLAB_API_KEY')

class TTSHandler:
    def __init__(self):
        self.tts_engine = ElevenlabsEngine(api_key=ELVEN_LAB_API_KEY)
        self.tts_stream = TextToAudioStream(self.tts_engine)

    def speak(self, text):
        self.tts_stream.feed(text)
        self.tts_stream.play_async()

def speak_response(text):
    tts_handler = TTSHandler()
    return tts_handler.speak(text)


