# backend/tts_service/main.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import websockets
import json
import uuid
import base64
import logging
from typing import Dict, List
import os
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Rime TTS Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Check API key on startup
rime_api_key = os.getenv("RIME_API_KEY")
if not rime_api_key:
    logger.error("❌ RIME_API_KEY not found in environment variables!")
    logger.error("💡 Create a .env file with: RIME_API_KEY=your_api_key_here")
    logger.error("🚨 TTS service will not work without valid Rime API key")
else:
    logger.info("✅ RIME_API_KEY found in environment")
    # Don't log the actual key for security
    logger.info(f"🔑 API key length: {len(rime_api_key)} characters")

class RimeTTSClient:
    def __init__(self, speaker="cove", api_key=None):
        self.speaker = speaker
        self.api_key = api_key or os.getenv("RIME_API_KEY")
        self.url = f"wss://users.rime.ai/ws?speaker={speaker}&modelId=mistv2&audioFormat=mp3"
        self.auth_headers = {
            "Authorization": f"Bearer {self.api_key}"
        }
        
    def text_to_tokens(self, text: str) -> List[str]:
        """Convert text to tokens for Rime streaming"""
        # Split text into words and add spaces
        words = text.split()
        tokens = []
        
        for i, word in enumerate(words):
            tokens.append(word)
            if i < len(words) - 1:  # Add space except for last word
                tokens.append(" ")
        
        # Add end-of-stream token
        tokens.append("<EOS>")
        return tokens
    
    async def generate_audio_stream(self, text: str, callback=None):
        """Generate audio stream from text using Rime API"""
        tokens = self.text_to_tokens(text)
        audio_data = b''
        
        logger.info(f"Starting Rime TTS generation for text: {text[:50]}...")
        logger.info(f"Generated {len(tokens)} tokens for Rime API")
        
        try:
            async with websockets.connect(self.url, additional_headers=self.auth_headers) as websocket:
                logger.info("Connected to Rime API successfully")
                
                # Send all tokens first
                await self._send_tokens(websocket, tokens)
                
                # Then wait for audio response (don't cancel - let it complete)
                audio_data = await self._receive_audio(websocket, callback)
                
                logger.info(f"Rime TTS generation completed. Audio size: {len(audio_data)} bytes")
                    
        except Exception as e:
            logger.error(f"Rime TTS API error: {e}")
            # Check if it's an authentication error
            if "401" in str(e) or "Unauthorized" in str(e):
                logger.error("Rime API authentication failed - check RIME_API_KEY")
            elif "403" in str(e) or "Forbidden" in str(e):
                logger.error("Rime API access forbidden - check API key permissions")
            elif "429" in str(e) or "rate limit" in str(e).lower():
                logger.error("Rime API rate limit exceeded")
            else:
                logger.error(f"Unknown Rime API error: {e}")
            raise e
        
        return audio_data
    
    async def _send_tokens(self, websocket, tokens):
        """Send tokens to Rime WebSocket"""
        try:
            logger.info(f"Sending {len(tokens)} tokens to Rime API")
            for i, token in enumerate(tokens):
                await websocket.send(token)
                await asyncio.sleep(0.01)  # Small delay between tokens
                if i % 10 == 0:  # Log progress every 10 tokens
                    logger.debug(f"Sent {i+1}/{len(tokens)} tokens")
            logger.info("All tokens sent to Rime API")
        except Exception as e:
            logger.error(f"Error sending tokens to Rime API: {e}")
            raise
    
    async def _receive_audio(self, websocket, callback=None):
        """Receive audio chunks from Rime WebSocket"""
        audio_data = b''
        chunk_count = 0
        max_wait_time = 30  # Maximum time to wait for audio generation
        start_time = asyncio.get_event_loop().time()
        
        try:
            logger.info("Starting to receive audio from Rime API...")
            
            while True:
                try:
                    # Add timeout to prevent infinite waiting
                    chunk = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    
                    if isinstance(chunk, bytes):
                        audio_data += chunk
                        chunk_count += 1
                        logger.info(f"Received audio chunk {chunk_count}: {len(chunk)} bytes")
                        
                        # Call callback for streaming if provided
                        if callback:
                            await callback(chunk)
                    else:
                        logger.debug(f"Received non-audio data: {type(chunk)}")
                        
                except asyncio.TimeoutError:
                    # Check if we've been waiting too long
                    elapsed = asyncio.get_event_loop().time() - start_time
                    if elapsed > max_wait_time:
                        logger.warning(f"Audio reception timeout after {elapsed:.1f}s")
                        break
                    elif chunk_count > 0:
                        # We got some audio, maybe it's done
                        logger.info(f"No more audio after {elapsed:.1f}s - assuming complete")
                        break
                    else:
                        # Still waiting for first chunk
                        logger.debug(f"Still waiting for first audio chunk after {elapsed:.1f}s...")
                        continue
                        
                except websockets.exceptions.ConnectionClosedOK:
                    logger.info(f"Rime API connection closed normally after {chunk_count} chunks")
                    break
                except websockets.exceptions.ConnectionClosedError as e:
                    logger.error(f"Rime API connection closed with error: {e}")
                    break
            
            logger.info(f"Audio reception complete: {chunk_count} chunks, {len(audio_data)} bytes total")
            
            if chunk_count == 0:
                logger.warning("No audio chunks received from Rime API")
            
        except Exception as e:
            logger.error(f"Error receiving audio from Rime API: {e}")
            raise
        
        return audio_data

class TTSSessionManager:
    def __init__(self):
        self.active_sessions: Dict[str, Dict] = {}
        self.rime_client = RimeTTSClient()
    
    async def handle_tts_request(self, websocket: WebSocket, request_data: dict):
        """Handle TTS generation request"""
        message_id = request_data.get("message_id")
        text = request_data.get("text", "")
        speech_type = request_data.get("speech_type", "system")
        
        if not text.strip():
            try:
                await websocket.send_json({
                    "type": "error",
                    "message_id": message_id,
                    "error": "Empty text provided"
                })
            except:
                pass  # Client might have disconnected
            return
        
        logger.info(f"Generating TTS for message {message_id}: {text[:50]}...")
        
        # Send TTS started signal
        try:
            await websocket.send_json({
                "type": "tts_started",
                "message_id": message_id,
                "text": text
            })
        except:
            logger.warning(f"Client disconnected before TTS started signal for message {message_id}")
            return
        
        try:
            # Define callback for streaming chunks
            async def stream_callback(chunk):
                try:
                    # Convert audio chunk to base64 for JSON transmission
                    chunk_b64 = base64.b64encode(chunk).decode('utf-8')
                    await websocket.send_json({
                        "type": "audio_chunk",
                        "message_id": message_id,
                        "chunk": chunk_b64,
                        "format": "mp3"
                    })
                except:
                    logger.warning(f"Client disconnected during audio streaming for message {message_id}")
                    raise Exception("Client disconnected")
            
            # Generate audio with streaming
            full_audio = await self.rime_client.generate_audio_stream(text, stream_callback)
            
            # Send completion signal
            try:
                await websocket.send_json({
                    "type": "tts_complete",
                    "message_id": message_id,
                    "total_size": len(full_audio)
                })
            except:
                logger.warning(f"Client disconnected before completion signal for message {message_id}")
                return
            
            logger.info(f"TTS generation complete for message {message_id}")
            
        except Exception as e:
            logger.error(f"TTS generation failed for message {message_id}: {e}")
            try:
                await websocket.send_json({
                    "type": "error",
                    "message_id": message_id,
                    "error": str(e)
                })
            except:
                logger.warning(f"Client disconnected, could not send error for message {message_id}")
                pass  # Client disconnected, can't send error

tts_manager = TTSSessionManager()

@app.websocket("/ws/tts")
async def websocket_tts_endpoint(websocket: WebSocket):
    """Main TTS WebSocket endpoint"""
    await websocket.accept()
    logger.info("New TTS WebSocket connection established")
    
    try:
        while True:
            # Receive request from Session Engine
            data = await websocket.receive_json()
            logger.info(f"Received TTS request: {data.get('message_id', 'unknown')}")
            
            # Handle the TTS request
            await tts_manager.handle_tts_request(websocket, data)
            
    except WebSocketDisconnect:
        logger.info("TTS WebSocket disconnected normally")
    except Exception as e:
        logger.error(f"TTS WebSocket error: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "error": str(e)
            })
        except:
            pass  # Connection might already be closed

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    rime_api_key = os.getenv("RIME_API_KEY")
    return {
        "status": "healthy", 
        "service": "rime-tts",
        "rime_api_configured": bool(rime_api_key),
        "rime_api_key_length": len(rime_api_key) if rime_api_key else 0
    }

