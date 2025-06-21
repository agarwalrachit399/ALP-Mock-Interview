# backend/session_engine/handlers/ws_question_handler.py

import logging
import json
import asyncio
import websockets
from fastapi import WebSocket
from starlette.websockets import WebSocketState
from session_engine.services.tts_handler import RimeTTSHandler  # Updated import
import uuid
import time

class WebSocketQuestionHandler:
    def __init__(self, websocket: WebSocket, tts: RimeTTSHandler, cancel_event: asyncio.Event):
        self.websocket = websocket
        self.tts = tts
        self.cancel_event = cancel_event

    async def speak_and_wait_simple(self, text, speech_type="retry"):
        """Simple speech method for retry messages using hybrid TTS (Rime + Browser fallback)"""
        message_id = str(uuid.uuid4())
        
        print(f"🔊 [RETRY] Speaking with hybrid TTS: {text[:50]}...")
        
        try:
            # Use the hybrid TTS handler (will send both display message and attempt Rime audio)
            await self.tts.speak_and_stream(self.websocket, text, message_id, speech_type)
            
            # Wait longer for hybrid TTS to complete (could be Rime audio generation + playback or browser TTS)
            await asyncio.sleep(5)  # Increased to account for both Rime and browser TTS possibilities
            
        except Exception as e:
            print(f"🚨 [RETRY] Hybrid TTS error, sending direct browser TTS fallback: {e}")
            # Final fallback: send text directly to frontend for browser TTS
            try:
                await self.websocket.send_json({
                    "type": "speech",
                    "text": text,
                    "speech_type": speech_type,
                    "message_id": message_id,
                    "fallback": True,  # Flag to indicate this should definitely use browser TTS
                    "has_rime_audio": False  # Explicitly disable Rime audio waiting
                })
                await asyncio.sleep(3)  # Wait for browser TTS to complete
            except Exception as fallback_error:
                print(f"🚨 [RETRY] Even final fallback failed: {fallback_error}")

    async def get_user_response(self, max_tries: int = 2) -> str:
        """
        Get user response via STT - now called AFTER TTS coordination is complete
        This method no longer needs to handle TTS timing since that's done at session level
        """
        print("🔍 [DEBUG] Starting get_user_response (TTS should already be complete)")
        
        try:
            await self.websocket.send_json({
                "type": "system",
                "text": "Listening for response..."
            })
        except Exception as e:
            print(f"🚨 [DEBUG] Failed to send listening message: {e}")
            return ""
        
        for attempt in range(max_tries):
            print(f"🔍 [DEBUG] STT Attempt {attempt + 1}")
            
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
                        "stop_duration": 2,
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
                                timeout=1.0  # Reasonable timeout
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
                    # Use hybrid TTS for retry messages
                    await self.speak_and_wait_simple("Please share your thoughts when you're ready.", "retry")
                    await self.websocket.send_json({
                        "type": "start_listening"
                    })
                except Exception as e:
                    print(f"Failed to send retry message: {e}")
        
        # Max retries reached
        logging.info("User did not respond after retries.")
        try:
            # Use hybrid TTS for skip message too
            await self.speak_and_wait_simple("No response detected after multiple attempts. Let's move on", "skip")
            # Give more time for hybrid TTS to complete (either Rime or browser)
            await asyncio.sleep(3)
        except Exception as e:
            print(f"Failed to send skip message: {e}")
        
        return ""