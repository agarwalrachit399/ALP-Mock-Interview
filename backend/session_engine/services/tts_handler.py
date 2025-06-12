import nest_asyncio
nest_asyncio.apply()
from RealtimeTTS import TextToAudioStream, EdgeEngine

class TTSHandler:
    def __init__(self):
        self.tts_engine =  EdgeEngine()
        self.tts_engine.set_voice("en-US-EmmaMultilingualNeural")
        self.tts_stream = TextToAudioStream(self.tts_engine,language='en')

    def speak(self, text):
        self.tts_stream.feed(text)
        self.tts_stream.play_async()
        try:
            if self.tts_stream.play_thread is not None:
                self.tts_stream.play_thread.join()
        finally:
            self.tts_stream.stop()

def speak_response(text):
    tts_handler = TTSHandler()
    return tts_handler.speak(text)



