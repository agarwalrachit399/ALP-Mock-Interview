# backend/session_engine/services/tts_handler.py
import asyncio
import websockets
import websockets.exceptions
import json
import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)

class RimeTTSHandler:
    def __init__(self, tts_service_url="ws://localhost:8003/ws/tts"):
        self.tts_service_url = tts_service_url
        self.tts_ws: Optional[websockets.WebSocketServerProtocol] = None
        self.connection_lock = asyncio.Lock()
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 3
    
    async def _ensure_connection(self):
        """Ensure TTS service connection is established"""
        try:
            logger.info(f"[DEBUG] _ensure_connection() START")
            logger.info(f"[DEBUG] Current tts_ws state: {self.tts_ws}")
            logger.info(f"[DEBUG] Target URL: {self.tts_service_url}")
            
            async with self.connection_lock:
                logger.info(f"[DEBUG] Acquired connection lock")
                
                # Check if we need a new connection
                logger.info(f"[DEBUG] Checking if new connection needed...")
                
                needs_new_connection = self.tts_ws is None
                logger.info(f"[DEBUG] tts_ws is None: {needs_new_connection}")
                
                if not needs_new_connection and hasattr(self.tts_ws, 'state'):
                    logger.info(f"[DEBUG] Checking existing connection state: {self.tts_ws.state.name}")
                    needs_new_connection = self.tts_ws.state.name in ['CLOSED', 'CLOSING']
                    logger.info(f"[DEBUG] Connection state check result: {needs_new_connection}")
                
                logger.info(f"[DEBUG] Final needs_new_connection: {needs_new_connection}")
                
                if needs_new_connection:
                    logger.info(f"[DEBUG] ENTERING try block for new connection")
                    try:
                        logger.info(f"[DEBUG] About to attempt connection to {self.tts_service_url}")
                        
                        self.tts_ws = await websockets.connect(
                            self.tts_service_url,
                            ping_interval=20,
                            ping_timeout=10
                        )
                        
                        logger.info(f"[DEBUG] Connection successful! Type: {type(self.tts_ws)}")
                        logger.info("Connected to Rime TTS service")
                        self.reconnect_attempts = 0
                        
                    except Exception as e:
                        logger.error(f"[DEBUG] Connection exception: {type(e).__name__}: {e}")
                        logger.error(f"[DEBUG] Full exception: {repr(e)}")
                        raise e
                else:
                    logger.info(f"[DEBUG] Using existing connection")
                    
            logger.info(f"[DEBUG] _ensure_connection() END - Success")
            
        except Exception as outer_e:
            logger.error(f"[DEBUG] OUTER EXCEPTION in _ensure_connection: {type(outer_e).__name__}: {outer_e}")
            logger.error(f"[DEBUG] Full outer exception: {repr(outer_e)}")
            raise outer_e

    async def speak_and_stream(self, session_websocket, text: str, message_id: str, speech_type: str = "system"):
        """Generate TTS and stream audio to frontend via session websocket"""
        try:
            logger.info(f"[speak_and_stream] Starting TTS for message {message_id}: {text[:50]}...")
            await self._ensure_connection()
            
            logger.info(f"Requesting TTS generation for message {message_id}: {text[:50]}...")
            
            # FIRST: Send the message in expected frontend format (question/speech) for display
            # Include a flag to indicate Rime TTS is available
            if speech_type == "question":
                await session_websocket.send_json({
                    "type": "question",
                    "text": text,
                    "message_id": message_id,
                    "has_rime_audio": True  # Signal that Rime audio will follow
                })
            else:
                await session_websocket.send_json({
                    "type": "speech",
                    "text": text,
                    "speech_type": speech_type,
                    "message_id": message_id,
                    "has_rime_audio": True  # Signal that Rime audio will follow
                })
            
            # Check connection is still valid before sending TTS request
            if (self.tts_ws is None or 
                (hasattr(self.tts_ws, 'state') and self.tts_ws.state.name in ['CLOSED', 'CLOSING'])):
                raise Exception("TTS WebSocket connection is not available")
            
            # Send TTS request to service
            tts_request = {
                "message_id": message_id,
                "text": text,
                "speech_type": speech_type
            }
            
            logger.info(f"[speak_and_stream] Sending TTS request to service for message {message_id}")
            await self.tts_ws.send(json.dumps(tts_request))
            
            # Stream responses back to session websocket
            audio_chunks_count = 0
            start_time = time.time()
            
            while True:
                try:
                    response = await asyncio.wait_for(self.tts_ws.recv(), timeout=30.0)
                    data = json.loads(response)
                    
                    # Forward all TTS service responses to session websocket
                    if data.get("message_id") == message_id:
                        if data["type"] == "tts_started":
                            logger.info(f"TTS generation started for message {message_id}")
                            # Send audio-specific started signal (in addition to question/speech above)
                            await session_websocket.send_json({
                                "type": "audio_generation_started",
                                "message_id": message_id
                            })
                            
                        elif data["type"] == "audio_chunk":
                            audio_chunks_count += 1
                            # Forward audio chunk to frontend
                            await session_websocket.send_json({
                                "type": "audio_chunk",
                                "message_id": message_id,
                                "chunk": data["chunk"],
                                "format": data.get("format", "mp3")
                            })
                            
                            # Log first chunk timing for latency monitoring
                            if audio_chunks_count == 1:
                                first_chunk_time = time.time() - start_time
                                logger.info(f"First audio chunk received in {first_chunk_time:.3f}s for message {message_id}")
                            
                        elif data["type"] == "tts_complete":
                            total_time = time.time() - start_time
                            logger.info(f"TTS generation complete for message {message_id} in {total_time:.3f}s ({audio_chunks_count} chunks)")
                            
                            await session_websocket.send_json({
                                "type": "audio_generation_complete",
                                "message_id": message_id,
                                "total_chunks": audio_chunks_count
                            })
                            break
                            
                        elif data["type"] == "error":
                            logger.error(f"TTS service error for message {message_id}: {data.get('error', 'Unknown error')}")
                            await session_websocket.send_json({
                                "type": "audio_generation_error",
                                "message_id": message_id,
                                "error": data.get("error", "TTS generation failed"),
                                "text": text  # Include original text for fallback
                            })
                            break
                    
                except asyncio.TimeoutError:
                    logger.error(f"TTS service timeout for message {message_id}")
                    await session_websocket.send_json({
                        "type": "tts_error",
                        "message_id": message_id,
                        "error": "TTS generation timeout"
                    })
                    break
                    
                except websockets.exceptions.ConnectionClosed:
                    logger.error(f"TTS service connection closed during generation for message {message_id}")
                    self.tts_ws = None  # Mark for reconnection
                    await session_websocket.send_json({
                        "type": "tts_error",
                        "message_id": message_id,
                        "error": "TTS service connection lost"
                    })
                    break
                    
        except Exception as e:
            logger.error(f"TTS streaming error for message {message_id}: {e}")
            try:
                await session_websocket.send_json({
                    "type": "tts_error",
                    "message_id": message_id,
                    "error": str(e)
                })
            except:
                pass  # Session websocket might be closed
    
    def speak(self, text: str):
        """Legacy speak method for compatibility - just logs"""
        logger.info(f"[TTS Legacy] Would speak: {text}")
    
    async def close(self):
        """Close TTS service connection"""
        if self.tts_ws is not None:
            try:
                # Check if connection is still open before trying to close
                if hasattr(self.tts_ws, 'state') and self.tts_ws.state.name not in ['CLOSED', 'CLOSING']:
                    await self.tts_ws.close()
                elif not getattr(self.tts_ws, 'closed', True):
                    await self.tts_ws.close()
                logger.info("TTS service connection closed")
            except Exception as e:
                logger.warning(f"Error closing TTS connection: {e}")
            finally:
                self.tts_ws = None

# Backward compatibility - keep the old class name
class TTSHandler(RimeTTSHandler):
    pass