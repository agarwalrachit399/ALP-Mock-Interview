from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
import asyncio
import json
import base64
import logging
from typing import Dict
from app.services.tts_service import tts_service
from app.models.tts import DirectTTSRequest, DirectTTSResponse, TTSConfig
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/generate", response_model=DirectTTSResponse)
async def generate_speech(request: DirectTTSRequest):
    """
    HTTP endpoint for direct speech generation
    """
    try:
        if not request.text.strip():
            return DirectTTSResponse(
                success=False,
                error="Empty text provided"
            )
        
        # Generate audio
        audio_data = await tts_service.generate_speech(
            text=request.text,
            speech_type=request.speech_type,
            config=request.config
        )
        
        if audio_data:
            # Convert to base64 for JSON response
            audio_b64 = base64.b64encode(audio_data).decode('utf-8')
            
            return DirectTTSResponse(
                success=True,
                audio_data=audio_b64,
                audio_size=len(audio_data)
            )
        else:
            return DirectTTSResponse(
                success=False,
                error="TTS generation failed"
            )
            
    except Exception as e:
        logger.error(f"TTS generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.websocket("/ws/tts")
async def websocket_tts_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time TTS streaming
    Maintains compatibility with original TTS service protocol
    """
    await websocket.accept()
    logger.info("New TTS WebSocket connection established")
    
    try:
        while True:
            # Receive request from client (Session Engine)
            data = await websocket.receive_json()
            logger.info(f"Received TTS request: {data.get('message_id', 'unknown')}")
            
            # Handle the TTS request
            await handle_websocket_tts_request(websocket, data)
            
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

async def handle_websocket_tts_request(websocket: WebSocket, request_data: dict):
    """Handle TTS generation request via WebSocket"""
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
        chunk_count = 0
        async def stream_callback(chunk: bytes):
            nonlocal chunk_count
            try:
                chunk_count += 1
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
        full_audio = await tts_service.generate_speech_with_streaming(
            text=text,
            chunk_callback=stream_callback,
            speech_type=speech_type
        )
        
        # Send completion signal
        try:
            await websocket.send_json({
                "type": "tts_complete",
                "message_id": message_id,
                "total_size": len(full_audio) if full_audio else 0,
                "total_chunks": chunk_count
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

@router.get("/health")
async def tts_health_check():
    """Health check for TTS service"""
    return {
        "status": "healthy",
        "service": "tts",
        "rime_api_configured": bool(settings.RIME_API_KEY),
        "rime_api_key_length": len(settings.RIME_API_KEY) if settings.RIME_API_KEY else 0
    }

@router.get("/config")
async def get_tts_config():
    """Get current TTS configuration"""
    return {
        "default_speaker": tts_service.default_config.speaker,
        "default_model": tts_service.default_config.model_id,
        "default_format": tts_service.default_config.audio_format,
        "rime_configured": bool(settings.RIME_API_KEY)
    }