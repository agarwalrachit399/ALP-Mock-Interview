from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.websockets import WebSocketState
import asyncio
import json
import threading
import logging
from concurrent.futures import ThreadPoolExecutor
from app.services.stt_service import stt_service
from app.models.stt import STTConfig, STTResponse

router = APIRouter()
logger = logging.getLogger(__name__)

# Thread pool for STT operations
stt_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="STT")

@router.post("/transcribe", response_model=STTResponse)
async def transcribe_audio(config: STTConfig):
    """
    HTTP endpoint for speech transcription (for testing)
    """
    try:
        transcript = await stt_service.transcribe_speech(
            stop_duration=config.stop_duration,
            max_wait=config.max_wait
        )
        
        return STTResponse(
            type="done",
            text=transcript
        )
    except Exception as e:
        logger.error(f"STT transcription error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.websocket("/ws/transcribe")
async def transcribe_websocket(websocket: WebSocket):
    """
    WebSocket endpoint for real-time speech transcription
    Maintains compatibility with original STT microservice
    """
    print("🔍 [STT] New STT WebSocket connection")
    await websocket.accept()
    
    cancel_event = threading.Event()
    transcription_task = None
    receive_task = None
    
    async def run_transcription_async(stop_duration, max_wait):
        """Run transcription in async context"""
        if cancel_event.is_set():
            return "Service cancelled"
        return await stt_service.transcribe_speech(stop_duration, max_wait, cancel_event)
    
    try:
        # Get configuration
        config_data = await websocket.receive_text()
        config = json.loads(config_data)
        stop_duration = config.get("stop_duration", 4)
        max_wait = config.get("max_wait", 10)
        
        print(f"🔍 [STT] Config received - stop: {stop_duration}s, max_wait: {max_wait}s")
        
        # Create transcription task
        transcription_task = asyncio.create_task(
            run_transcription_async(stop_duration, max_wait)
        )
        
        # Create receive task for cancel commands
        receive_task = asyncio.create_task(websocket.receive_text())
        
        while True:
            print("🔍 [STT] Waiting for transcription or cancel command")
            done, pending = await asyncio.wait(
                [transcription_task, receive_task],
                return_when=asyncio.FIRST_COMPLETED,
                timeout=1.0  # Check periodically
            )
            
            print(f"🔍 [STT] Task completed - done: {len(done)}")
            
            # Handle completed transcription
            if transcription_task in done:
                try:
                    transcript = transcription_task.result()
                    await websocket.send_text(json.dumps({
                        "type": "done",
                        "text": transcript
                    }))
                    print(f"🔍 [STT] Sent transcription result: '{transcript}'")
                except Exception as e:
                    logger.error(f"Transcription error: {e}")
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": str(e)
                    }))
                break
                
            # Handle cancel command
            if receive_task in done:
                try:
                    msg_text = receive_task.result()
                    msg = json.loads(msg_text)
                    print(f"🔍 [STT] Received message: {msg}")
                    
                    if msg.get("command") == "cancel":
                        print("🚨 [STT] CANCEL COMMAND RECEIVED!")
                        cancel_event.set()
                        print("🚨 [STT] Cancel event set in STT")
                        await websocket.send_text(json.dumps({
                            "type": "cancelled",
                            "text": "Transcription manually cancelled"
                        }))
                        break
                        
                except WebSocketDisconnect:
                    print("🔌 STT Client disconnected naturally")
                    cancel_event.set()
                    break
                except Exception as e:
                    print(f"Error processing WebSocket message: {e}")
                    break
                
                # Restart receive task for next command
                receive_task = asyncio.create_task(websocket.receive_text())
            
            # Cancel pending tasks that we're not waiting for anymore
            for task in pending:
                if task != transcription_task and task != receive_task:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
                        
    except WebSocketDisconnect:
        print("🔌 STT Client disconnected during setup")
        cancel_event.set()
    except Exception as e:
        print(f"❌ STT Error: {e}")
        try:
            await websocket.send_text(json.dumps({"type": "error", "message": str(e)}))
        except:
            pass  # WebSocket might already be closed
    finally:
        print("🧹 [STT] Starting cleanup...")
        
        # Signal cancellation
        cancel_event.set()
        
        # Cancel and cleanup transcription task
        if transcription_task and not transcription_task.done():
            transcription_task.cancel()
            try:
                await asyncio.wait_for(transcription_task, timeout=5.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                logger.warning("Transcription task cancellation timeout")
        
        # Cancel and cleanup receive task
        if receive_task and not receive_task.done():
            receive_task.cancel()
            try:
                await receive_task
            except asyncio.CancelledError:
                pass
        
        # Close WebSocket if still open
        try:
            if websocket.client_state != WebSocketState.DISCONNECTED:
                await websocket.close()
        except:
            pass  # Already closed
            
        print("🧹 [STT] Cleanup complete")

@router.get("/health")
async def stt_health_check():
    """Health check for STT service"""
    from app.core.config import settings
    return {
        "status": "healthy",
        "service": "stt",
        "speechmatics_configured": bool(settings.SPEECHMATICS_API_KEY)
    }