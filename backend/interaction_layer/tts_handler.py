from RealtimeTTS import TextToAudioStream, EdgeEngine

class TTSHandler:
    def __init__(self):
        self.tts_engine =  EdgeEngine()
        self.tts_engine.set_voice("en-US-EmmaMultilingualNeural")
        self.tts_stream = TextToAudioStream(self.tts_engine,language='en')

    def speak(self, text):
        self.tts_stream.feed(text)
        self.tts_stream.play()

def speak_response(text):
    tts_handler = TTSHandler()
    return tts_handler.speak(text)


