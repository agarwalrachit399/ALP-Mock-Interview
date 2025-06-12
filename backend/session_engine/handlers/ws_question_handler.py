import logging
from fastapi import WebSocket
from session_engine.services.stt_handler import transcribe_speech
from session_engine.services.tts_handler import TTSHandler

class WebSocketQuestionHandler:
    def __init__(self, websocket: WebSocket, tts: TTSHandler):
        self.websocket = websocket
        self.tts = tts

    async def ask_question(self, text: str):
        logging.info(f"Bot asked: {text}")
        await self.websocket.send_json({
            "type": "question",
            "text": text
        })
        self.tts.speak(text)

    async def get_user_response(self, max_tries: int = 2) -> str:
        await self.websocket.send_json({
            "type": "system",
            "text": "Listening for response..."
        })

        for attempt in range(max_tries):
            response = transcribe_speech(stop_duration=4.0, max_wait=10)

            if response.strip():
                logging.info(f"User said: {response}")
                await self.websocket.send_json({
                    "type": "answer",
                    "text": response
                })
                return response.strip()

            if attempt < max_tries - 1:
                logging.info(f"No response detected. Attempt {attempt + 1}/{max_tries}. Re-prompting user.")
                self.tts.speak("Please share your thoughts when you're ready.")

        logging.info("User did not respond after retries.")
        await self.websocket.send_json({
            "type": "system",
            "text": "No response detected after multiple attempts."
        })
        return ""
