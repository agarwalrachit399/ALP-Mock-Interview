import asyncio
import websockets
import json

TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiNjg0OWI1ZTYxMDcwMzViNjQ2ZTFlMzA3IiwiZW1haWwiOiJyYWNoaXRAZXhhbXBsZS5jb20iLCJleHAiOjE3NDk3NTg1NDJ9.nB-05WVXm3hWxgftpDciHNcJWBtJdMfkUfGa7zZ7Ybk"
URI = "ws://localhost:8001/session/ws/interview?token=" + TOKEN

async def test():
    async with websockets.connect(
        URI,
        additional_headers=[("Authorization", TOKEN)]
    ) as ws:
        while True:
            try:
                msg = await ws.recv()
                try:
                    data = json.loads(msg)
                except json.JSONDecodeError:
                    print("Bot (raw):", msg)
                    continue

                if data["type"] == "question":
                    print(f"\n🧠 Question: {data['text']}")
                elif data["type"] == "system":
                    print(f"\n⚙️  System: {data['text']}")
                elif data["type"] == "answer":
                    print(f"\n📜 STT Response: {data['text']}")
                elif data["type"] == "complete":
                    print(f"\n✅ {data['text']}")
                    break
                elif data["type"] == "terminate":
                    print(f"\n❌ Interview terminated. Reason: {data.get('reason', 'unknown')}")
                    break
                else:
                    print(f"\n💬 Unknown message type: {data}")
            except websockets.exceptions.ConnectionClosed as e:
                print(f"\n🔌 Connection closed: {e}")
                break

asyncio.run(test())
