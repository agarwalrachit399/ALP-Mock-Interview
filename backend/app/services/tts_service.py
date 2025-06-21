import asyncio
import websockets
import websockets.exceptions
import base64
import logging
from typing import Optional, List, Callable
from app.core.config import settings
from app.models.tts import TTSConfig

logger = logging.getLogger(__name__)

class RimeTTSClient:
    def __init__(self, speaker="cove", model_id="mistv2", audio_format="mp3"):
        self.speaker = speaker
        self.model_id = model_id
        self.audio_format = audio_format
        self.api_key = settings.RIME_API_KEY
        self.url = f"wss://users.rime.ai/ws?speaker={speaker}&modelId={model_id}&audioFormat={audio_format}"
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
    
    async def generate_audio_stream(self, text: str, callback: Optional[Callable] = None) -> bytes:
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
                
                # Then wait for audio response
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
                        logger.debug(f"Received audio chunk {chunk_count}: {len(chunk)} bytes")
                        
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

class TTSService:
    """Text-to-Speech service for the monolith"""
    
    def __init__(self):
        self.default_config = TTSConfig()
        
    async def generate_speech(self, text: str, speech_type: str = "system", 
                             config: Optional[TTSConfig] = None) -> Optional[bytes]:
        """
        Generate speech audio from text
        
        Args:
            text: Text to convert to speech
            speech_type: Type of speech for context
            config: TTS configuration (optional)
            
        Returns:
            Audio data as bytes or None if failed
        """
        if not text.strip():
            logger.warning("Empty text provided for TTS generation")
            return None
            
        if not settings.RIME_API_KEY:
            logger.error("RIME_API_KEY not configured")
            return None
            
        # Use provided config or default
        tts_config = config or self.default_config
        
        logger.info(f"🔊 [TTS] Generating speech: {text[:50]}... (type: {speech_type})")
        
        try:
            # Create Rime client with config
            client = RimeTTSClient(
                speaker=tts_config.speaker,
                model_id=tts_config.model_id,
                audio_format=tts_config.audio_format
            )
            
            # Generate audio
            audio_data = await client.generate_audio_stream(text)
            
            logger.info(f"✅ [TTS] Speech generation completed: {len(audio_data)} bytes")
            return audio_data
            
        except Exception as e:
            logger.error(f"❌ [TTS] Speech generation failed: {e}")
            return None
    
    async def generate_speech_with_streaming(self, text: str, 
                                           chunk_callback: Callable[[bytes], None],
                                           speech_type: str = "system",
                                           config: Optional[TTSConfig] = None) -> Optional[bytes]:
        """
        Generate speech with streaming callback for real-time playback
        
        Args:
            text: Text to convert to speech
            chunk_callback: Async function called for each audio chunk
            speech_type: Type of speech for context
            config: TTS configuration (optional)
            
        Returns:
            Complete audio data as bytes or None if failed
        """
        if not text.strip():
            logger.warning("Empty text provided for streaming TTS generation")
            return None
            
        if not settings.RIME_API_KEY:
            logger.error("RIME_API_KEY not configured")
            return None
            
        # Use provided config or default
        tts_config = config or self.default_config
        
        logger.info(f"🔊 [TTS STREAM] Generating speech with streaming: {text[:50]}...")
        
        try:
            # Create Rime client with config
            client = RimeTTSClient(
                speaker=tts_config.speaker,
                model_id=tts_config.model_id,
                audio_format=tts_config.audio_format
            )
            
            # Generate audio with streaming callback
            audio_data = await client.generate_audio_stream(text, chunk_callback)
            
            logger.info(f"✅ [TTS STREAM] Streaming speech generation completed: {len(audio_data)} bytes")
            return audio_data
            
        except Exception as e:
            logger.error(f"❌ [TTS STREAM] Streaming speech generation failed: {e}")
            return None
    
    def speak_sync(self, text: str) -> None:
        """
        Legacy synchronous speak method for compatibility
        Just logs the text (audio would be handled by frontend)
        """
        logger.info(f"[TTS Legacy] Would speak: {text}")
    
    async def speak_async(self, text: str) -> Optional[bytes]:
        """
        Async version of speak that returns audio data
        """
        return await self.generate_speech(text)

# Global TTS service instance
tts_service = TTSService()