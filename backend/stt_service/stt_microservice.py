from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState
import asyncio
import json
import threading
import logging
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from stt_handler1 import STTTranscriber  # must expose class

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Global executor and task tracking
executor = None
active_tasks = set()
shutdown_event = threading.Event()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global executor
    executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="STT")
    logging.info("STT ThreadPoolExecutor started")
    
    yield
    
    # Shutdown
    logging.info("Shutting down STT service...")
    shutdown_event.set()
    
    # Cancel all active tasks
    for task in list(active_tasks):
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            
    # Shutdown executor with timeout
    if executor:
        logging.info("Shutting down executor...")
        try:
            # Use asyncio timeout for executor shutdown
            await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None, lambda: executor.shutdown(wait=True)
                ),
                timeout=10.0
            )
            logging.info("Executor shutdown complete")
        except asyncio.TimeoutError:
            logging.warning("Executor shutdown timeout - forcing shutdown")
            executor.shutdown(wait=False, cancel_futures=True)
        except Exception as e:
            logging.error(f"Error during executor shutdown: {e}")
            executor.shutdown(wait=False, cancel_futures=True)

app = FastAPI(lifespan=lifespan)

@app.websocket("/ws/transcribe")
async def transcribe_websocket(websocket: WebSocket):
    print("🔍 [STT DEBUG] New STT WebSocket connection")
    await websocket.accept()
    
    cancel_event = threading.Event()
    transcriber = None
    transcription_task = None
    receive_task = None
    
    def run_transcription(stop_duration, max_wait):
        nonlocal transcriber
        if shutdown_event.is_set():
            return "Service shutting down"
        transcriber = STTTranscriber(stop_duration, max_wait, cancel_event)
        return transcriber.run_transcription()
    
    try:
        # Get configuration
        config_data = await websocket.receive_text()
        config = json.loads(config_data)
        stop_duration = config.get("stop_duration", 4)
        max_wait = config.get("max_wait", 10)
        
        # Check if service is shutting down
        if shutdown_event.is_set():
            await websocket.send_text(json.dumps({
                "type": "error",
                "message": "Service is shutting down"
            }))
            return
        
        loop = asyncio.get_event_loop()
        
        # Create transcription task
        transcription_task = loop.run_in_executor(
            executor, run_transcription, stop_duration, max_wait
        )
        active_tasks.add(transcription_task)
        
        # Create receive task
        receive_task = asyncio.create_task(websocket.receive_text())
        active_tasks.add(receive_task)
        
        while not shutdown_event.is_set():
            print("🔍 [STT DEBUG] Waiting for transcription or cancel command")
            done, pending = await asyncio.wait(
                [transcription_task, receive_task],
                return_when=asyncio.FIRST_COMPLETED,
                timeout=1.0  # Check shutdown event every second
            )
            
            print(f"🔍 [STT DEBUG] Task completed - done: {len(done)}")
            
            # Handle completed tasks
            if transcription_task in done:
                try:
                    transcript = transcription_task.result()
                    await websocket.send_text(json.dumps({
                        "type": "done",
                        "text": transcript
                    }))
                except Exception as e:
                    logging.error(f"Transcription error: {e}")
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": str(e)
                    }))
                break
                
            if receive_task in done:
                try:
                    msg_text = receive_task.result()
                    msg = json.loads(msg_text)
                    print(f"🔍 [STT DEBUG] Received message: {msg}")
                    
                    if msg.get("command") == "cancel":
                        print("🚨 [STT DEBUG] CANCEL COMMAND RECEIVED!")
                        cancel_event.set()
                        print("🚨 [STT DEBUG] Cancel event set in STT")
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
                active_tasks.add(receive_task)
            
            # If no tasks completed, check shutdown and continue
            if not done and shutdown_event.is_set():
                break
            
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
        print("🧹 [STT DEBUG] Starting cleanup...")
        
        # Signal cancellation
        cancel_event.set()
        
        # Cancel and cleanup transcription task
        if transcription_task and not transcription_task.done():
            transcription_task.cancel()
            try:
                await asyncio.wait_for(transcription_task, timeout=5.0)
            except (asyncio.CancelledError, asyncio.TimeoutError):
                logging.warning("Transcription task cancellation timeout")
        
        # Remove from active tasks
        if transcription_task:
            active_tasks.discard(transcription_task)
            
        # Cancel and cleanup receive task
        if receive_task and not receive_task.done():
            receive_task.cancel()
            try:
                await receive_task
            except asyncio.CancelledError:
                pass
        
        if receive_task:
            active_tasks.discard(receive_task)
        
        # Close WebSocket if still open
        try:
            if websocket.client_state != WebSocketState.DISCONNECTED:
                await websocket.close()
        except:
            pass  # Already closed
            
        print("🧹 [STT DEBUG] Cleanup complete")

