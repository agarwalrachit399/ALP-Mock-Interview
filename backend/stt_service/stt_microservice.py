from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState
import asyncio
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from stt_handler1 import STTTranscriber  # must expose class

app = FastAPI()
executor = ThreadPoolExecutor()

@app.websocket("/ws/transcribe")
async def transcribe_websocket(websocket: WebSocket):
    print("🔍 [STT DEBUG] New STT WebSocket connection")
    await websocket.accept()
    cancel_event = threading.Event()
    transcriber = None
    
    def run_transcription(stop_duration, max_wait):
        nonlocal transcriber
        transcriber = STTTranscriber(stop_duration, max_wait, cancel_event)
        return transcriber.run_transcription()
    
    transcription_task = None
    receive_task = None
    
    try:
        config_data = await websocket.receive_text()
        config = json.loads(config_data)
        stop_duration = config.get("stop_duration", 4)
        max_wait = config.get("max_wait", 10)
        
        loop = asyncio.get_event_loop()
        transcription_task = loop.run_in_executor(
            executor, run_transcription, stop_duration, max_wait
        )
        
        receive_task = asyncio.create_task(websocket.receive_text())
        
        while True:
            print("🔍 [STT DEBUG] Waiting for transcription or cancel command")
            done, pending = await asyncio.wait(
                [transcription_task, receive_task],
                return_when=asyncio.FIRST_COMPLETED,
            )
            print(f"🔍 [STT DEBUG] Task completed - done: {len(done)}")
            # Cancel all pending tasks to prevent orphaned tasks
            for task in pending:
                task.cancel()
                try:
                    await task  # Wait for cancellation to complete
                except asyncio.CancelledError:
                    pass  # Expected when cancelling
            
            if transcription_task in done:
                transcript = transcription_task.result()
                await websocket.send_text(json.dumps({
                    "type": "done",
                    "text": transcript
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
                    # Client disconnected naturally - this is expected
                    print("🔌 STT Client disconnected naturally")
                    cancel_event.set()
                    break
                
                # Restart receive task for next command
                receive_task = asyncio.create_task(websocket.receive_text())
                
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
        # Cleanup: Cancel any remaining tasks
        cancel_event.set()
        
        if transcription_task and not transcription_task.done():
            transcription_task.cancel()
            try:
                await transcription_task
            except asyncio.CancelledError:
                pass
                
        if receive_task and not receive_task.done():
            receive_task.cancel()
            try:
                await receive_task
            except asyncio.CancelledError:
                pass
                
        try:
            if not websocket.client_state == WebSocketState.DISCONNECTED:
                await websocket.close()
        except:
            pass  # Already closed

