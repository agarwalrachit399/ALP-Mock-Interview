import asyncio
import websockets
import json

async def test_transcribe_with_cancel():
    uri = "ws://localhost:8002/ws/transcribe"
    async with websockets.connect(uri) as websocket:
        await websocket.send(json.dumps({
            "stop_duration": 4,
            "max_wait": 20
        }))

        async def send_cancel():
            await asyncio.sleep(10)  # cancel after 5 seconds
            await websocket.send(json.dumps({"command": "cancel"}))

        cancel_task = asyncio.create_task(send_cancel())

        try:
            while True:
                message = await websocket.recv()
                data = json.loads(message)
                print(f"[{data['type']}] {data.get('text', data.get('message', ''))}")
                if data["type"] in ["done", "cancelled", "error"]:
                    break
        finally:
            cancel_task.cancel()

asyncio.run(test_transcribe_with_cancel())
