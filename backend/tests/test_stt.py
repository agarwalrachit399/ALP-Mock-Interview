import asyncio
import websockets
import json
import requests

BASE_URL = "http://localhost:8000"

async def test_stt_websocket():
    """Test STT WebSocket functionality (mimics original microservice)"""
    print("Testing STT WebSocket Interface...\n")
    
    uri = f"ws://localhost:8000/stt/ws/transcribe"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to STT WebSocket")
            
            # Send configuration
            config = {
                "stop_duration": 4,
                "max_wait": 20
            }
            await websocket.send(json.dumps(config))
            print(f"📤 Sent config: {config}")
            
            # Optional: Send cancel after some time (uncomment to test cancellation)
            async def send_cancel():
                await asyncio.sleep(10)  # Cancel after 10 seconds
                await websocket.send(json.dumps({"command": "cancel"}))
                print("📤 Sent cancel command")
            
            cancel_task = asyncio.create_task(send_cancel())
            
            print("🎤 Listening for speech... (speak something or wait for timeout)")
            
            # Listen for responses
            try:
                while True:
                    message = await websocket.recv()
                    data = json.loads(message)
                    
                    print(f"📥 Received: {data}")
                    
                    if data["type"] == "done":
                        print(f"✅ Transcription completed: '{data.get('text', '')}'")
                        break
                    elif data["type"] == "cancelled":
                        print(f"⚠️ Transcription cancelled: {data.get('text', '')}")
                        break
                    elif data["type"] == "error":
                        print(f"❌ Transcription error: {data.get('message', '')}")
                        break
                        
            except websockets.exceptions.ConnectionClosed:
                print("🔌 WebSocket connection closed")
                
    except Exception as e:
        print(f"❌ WebSocket test failed: {e}")

def test_stt_http():
    """Test STT HTTP endpoint"""
    print("Testing STT HTTP Interface...\n")
    
    try:
        config = {
            "stop_duration": 4,
            "max_wait": 20
        }
        
        print(f"📤 Sending HTTP request with config: {config}")
        print("🎤 Speak something or wait for timeout...")
        
        response = requests.post(f"{BASE_URL}/stt/transcribe", json=config, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ HTTP transcription completed: '{result.get('text', '')}'")
        else:
            print(f"❌ HTTP request failed: {response.status_code} - {response.text}")
            
    except requests.exceptions.Timeout:
        print("⏰ HTTP request timed out")
    except Exception as e:
        print(f"❌ HTTP test failed: {e}")

def test_stt_health():
    """Test STT health endpoint"""
    print("Testing STT Health Check...\n")
    
    try:
        response = requests.get(f"{BASE_URL}/stt/health")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ STT Health Check:")
            print(f"   - Status: {result.get('status')}")
            print(f"   - Service: {result.get('service')}")
            print(f"   - Speechmatics Configured: {result.get('speechmatics_configured')}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Health check error: {e}")

async def test_direct_service_call():
    """Test direct service call (internal monolith usage)"""
    print("Testing Direct STT Service Call...\n")
    
    try:
        from app.services.stt_service import stt_service
        
        print("🎤 Testing direct service call... (speak something)")
        
        # Test direct async call
        transcript = await stt_service.transcribe_speech(
            stop_duration=4,
            max_wait=20
        )
        
        print(f"✅ Direct service call completed: '{transcript}'")
        
    except Exception as e:
        print(f"❌ Direct service call failed: {e}")

async def main():
    """Run all STT tests"""
    print("🎤 STT Service Testing Suite")
    print("=" * 50)
    
    # Test 1: Health check
    # test_stt_health()
    # print()
    
    # Test 2: HTTP endpoint
    # test_stt_http()
    # print()
    
    # Test 3: WebSocket interface  
    await test_stt_websocket()
    print()
    
    # Test 4: Direct service call
    print("Note: Direct service call test requires the app to be running.")
    print("You can test direct calls from within the application.\n")
    
    print("🎉 STT testing complete!")
    print("\nTo test speech recognition:")
    print("1. Make sure you have a microphone connected")
    print("2. Uncomment the test you want to run")
    print("3. Run the script and speak when prompted")

if __name__ == "__main__":
    asyncio.run(main())