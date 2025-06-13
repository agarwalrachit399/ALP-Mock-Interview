# session_engine/handlers/ws_question_handler.py

import logging
import json
import asyncio
import websockets
from fastapi import WebSocket
from starlette.websockets import WebSocketState
from session_engine.services.tts_handler import TTSHandler

class WebSocketQuestionHandler:
    def __init__(self, websocket: WebSocket, tts: TTSHandler, cancel_event: asyncio.Event):
        self.websocket = websocket
        self.tts = tts
        self.cancel_event = cancel_event

    async def ask_question(self, text: str):
        # Check for cancellation before asking
        if self.cancel_event.is_set():
            return
            
        logging.info(f"Bot asked: {text}")
        try:
            await self.websocket.send_json({
                "type": "question",
                "text": text
            })
            self.tts.speak(text)
        except Exception as e:
            logging.error(f"Error asking question: {e}")
            self.cancel_event.set()
        
        print("👂 Awaiting user response...")

    async def get_user_response(self, max_tries: int = 2) -> str:
        print("🔍 [DEBUG] Starting get_user_response")
        
        try:
            await self.websocket.send_json({
                "type": "system",
                "text": "Listening for response..."
            })
        except Exception as e:
            print(f"🚨 [DEBUG] Failed to send listening message: {e}")
            return ""
        
        for attempt in range(max_tries):
            print(f"🔍 [DEBUG] Attempt {attempt + 1}")
            
            if self.cancel_event.is_set():
                print("🚨 [DEBUG] Cancel event already set before attempt - returning immediately")
                return ""

            try:
                print("🔍 [DEBUG] Attempting to connect to STT...")
                async with websockets.connect("ws://localhost:8002/ws/transcribe") as stt_ws:
                    print("🔍 [DEBUG] Connected to STT successfully")
                    
                    # Check cancellation AFTER connecting
                    if self.cancel_event.is_set():
                        print("🚨 [DEBUG] Cancel event detected after STT connection - sending cancel immediately")
                        try:
                            await stt_ws.send(json.dumps({"command": "cancel"}))
                            print("🚨 [DEBUG] Cancel command sent to STT successfully")
                        except Exception as e:
                            print(f"🚨 [DEBUG] Failed to send cancel to STT: {e}")
                        return ""
                    
                    # Send STT configuration
                    await stt_ws.send(json.dumps({
                        "stop_duration": 4,
                        "max_wait": 90
                    }))
                    print("🔍 [DEBUG] STT config sent")
                    
                    # Check cancellation again AFTER configuration
                    if self.cancel_event.is_set():
                        print("🚨 [DEBUG] Cancel event detected after STT config - sending cancel")
                        try:
                            await stt_ws.send(json.dumps({"command": "cancel"}))
                            print("🚨 [DEBUG] Cancel command sent to STT successfully")
                        except Exception as e:
                            print(f"🚨 [DEBUG] Failed to send cancel to STT: {e}")
                        return ""
                    
                    # Main STT loop
                    while True:
                        print(f"🔍 [DEBUG] STT loop - cancel_event.is_set(): {self.cancel_event.is_set()}")
                        
                        # Check cancellation
                        if self.cancel_event.is_set():
                            print("🚨 [DEBUG] Cancel event detected in STT loop - sending cancel to STT")
                            try:
                                await stt_ws.send(json.dumps({"command": "cancel"}))
                                print("🚨 [DEBUG] Cancel command sent to STT successfully")
                            except Exception as e:
                                print(f"🚨 [DEBUG] Failed to send cancel to STT: {e}")
                            return ""
                        
                        # Check WebSocket state
                        if self.websocket.client_state != WebSocketState.CONNECTED:
                            try:
                                await stt_ws.send(json.dumps({"command": "cancel"}))
                                await stt_ws.close(code=1000, reason="Interview ended")
                            except:
                                pass
                            return ""
                        
                        # Race between STT response and cancellation
                        try:
                            stt_task = asyncio.create_task(stt_ws.recv())
                            cancel_task = asyncio.create_task(self.cancel_event.wait())
                            
                            print("🔍 [DEBUG] Starting race between STT and cancel event")
                            
                            done, pending = await asyncio.wait(
                                [stt_task, cancel_task],
                                return_when=asyncio.FIRST_COMPLETED,
                                timeout=1.0  # Add back reasonable timeout
                            )
                            
                            # Cancel pending tasks
                            for task in pending:
                                task.cancel()
                                try:
                                    await task
                                except asyncio.CancelledError:
                                    pass
                            
                            print(f"🔍 [DEBUG] Race completed - done tasks: {len(done)}, pending: {len(pending)}")
                            
                            # Handle results
                            if cancel_task in done:
                                print("🚨 [DEBUG] CANCEL TASK WON THE RACE!")
                                try:
                                    await stt_ws.send(json.dumps({"command": "cancel"}))
                                    print("🚨 [DEBUG] Cancel command sent to STT successfully")
                                except Exception as e:
                                    print(f"🚨 [DEBUG] Failed to send cancel to STT: {e}")
                                return ""
                            
                            if stt_task in done:
                                try:
                                    message = stt_task.result()
                                    data = json.loads(message)
                                    
                                    if data["type"] == "done":
                                        transcript = data["text"].strip()
                                        if transcript:
                                            logging.info(f"User said: {transcript}")
                                            try:
                                                await self.websocket.send_json({
                                                    "type": "answer",
                                                    "text": transcript
                                                })
                                            except:
                                                pass
                                            return transcript
                                        else:
                                            print("🔍 [DEBUG] Empty transcript - breaking to retry")
                                            break
                                            
                                    elif data["type"] == "cancelled":
                                        print("🔍 [DEBUG] STT was cancelled")
                                        return ""
                                        
                                    elif data["type"] == "error":
                                        logging.error(f"STT Microservice Error: {data['message']}")
                                        break
                                        
                                except Exception as e:
                                    logging.error(f"Error processing STT response: {e}")
                                    break
                            
                            # No tasks completed (timeout)
                            if not done:
                                print("🔍 [DEBUG] Race timeout - continuing loop")
                                continue
                                
                        except Exception as e:
                            logging.error(f"Error in STT communication: {e}")
                            break
                            
            except Exception as e:
                logging.exception("Error connecting to STT microservice")
                if self.cancel_event.is_set():
                    return ""
            
            # Check cancellation before retry
            if self.cancel_event.is_set():
                print("🚨 [DEBUG] Cancel event set - not retrying")
                return ""
                
            if attempt < max_tries - 1:
                logging.info(f"No response detected. Attempt {attempt + 1}/{max_tries}. Re-prompting user.")
                try:
                    self.tts.speak("Please share your thoughts when you're ready.")
                except:
                    pass
        
        # Max retries reached
        logging.info("User did not respond after retries.")
        try:
            await self.websocket.send_json({
                "type": "system",
                "text": "No response detected after multiple attempts."
            })
        except:
            pass
        
        return ""