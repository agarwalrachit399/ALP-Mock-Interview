import asyncio
import websockets
import json
import requests
import base64
import uuid

BASE_URL = "http://localhost:8000"

def test_tts_health():
    """Test TTS health check"""
    print("Testing TTS Health Check...\n")
    
    try:
        response = requests.get(f"{BASE_URL}/tts/health")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ TTS Health Check:")
            print(f"   - Status: {result.get('status')}")
            print(f"   - Service: {result.get('service')}")
            print(f"   - Rime API Configured: {result.get('rime_api_configured')}")
            print(f"   - API Key Length: {result.get('rime_api_key_length')}")
        else:
            print(f"❌ Health check failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Health check error: {e}")

def test_tts_config():
    """Test TTS configuration endpoint"""
    print("Testing TTS Configuration...\n")
    
    try:
        response = requests.get(f"{BASE_URL}/tts/config")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ TTS Configuration:")
            print(f"   - Default Speaker: {result.get('default_speaker')}")
            print(f"   - Default Model: {result.get('default_model')}")
            print(f"   - Default Format: {result.get('default_format')}")
            print(f"   - Rime Configured: {result.get('rime_configured')}")
        else:
            print(f"❌ Config check failed: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Config check error: {e}")

def test_tts_http():
    """Test TTS HTTP endpoint"""
    print("Testing TTS HTTP Interface...\n")
    
    try:
        request_data = {
            "text": "Hello! This is a test of the text to speech service.",
            "speech_type": "test"
        }
        
        print(f"📤 Sending HTTP TTS request: '{request_data['text']}'")
        
        response = requests.post(f"{BASE_URL}/tts/generate", json=request_data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            if result["success"]:
                audio_size = result.get("audio_size", 0)
                print(f"✅ TTS generation successful!")
                print(f"   - Audio size: {audio_size} bytes")
                print(f"   - Audio data: {result['audio_data'][:50]}... (base64)")
                
                # Optionally save audio to file
                if result.get("audio_data"):
                    audio_bytes = base64.b64decode(result["audio_data"])
                    with open("test_tts_output.mp3", "wb") as f:
                        f.write(audio_bytes)
                    print(f"   - Audio saved to: test_tts_output.mp3")
            else:
                print(f"❌ TTS generation failed: {result.get('error')}")
        else:
            print(f"❌ HTTP request failed: {response.status_code} - {response.text}")
            
    except requests.exceptions.Timeout:
        print("⏰ HTTP request timed out")
    except Exception as e:
        print(f"❌ HTTP test failed: {e}")

async def test_tts_websocket():
    """Test TTS WebSocket functionality"""
    print("Testing TTS WebSocket Interface...\n")
    
    uri = f"ws://localhost:8000/tts/ws/tts"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ Connected to TTS WebSocket")
            
            # Send TTS request
            message_id = str(uuid.uuid4())
            request_data = {
                "message_id": message_id,
                "text": "Hello from the WebSocket TTS test! This should be converted to speech.",
                "speech_type": "test"
            }
            
            await websocket.send(json.dumps(request_data))
            print(f"📤 Sent TTS request: {message_id}")
            
            # Listen for responses
            chunk_count = 0
            total_audio_size = 0
            
            try:
                while True:
                    message = await websocket.recv()
                    data = json.loads(message)
                    
                    print(f"📥 Received: {data.get('type')} for message {data.get('message_id')}")
                    
                    if data["type"] == "tts_started":
                        print(f"🔊 TTS generation started for: '{data.get('text', '')[:50]}...'")
                        
                    elif data["type"] == "audio_chunk":
                        chunk_count += 1
                        chunk_size = len(base64.b64decode(data["chunk"]))
                        total_audio_size += chunk_size
                        print(f"🎵 Audio chunk {chunk_count}: {chunk_size} bytes")
                        
                    elif data["type"] == "tts_complete":
                        print(f"✅ TTS generation completed!")
                        print(f"   - Total chunks: {data.get('total_chunks', chunk_count)}")
                        print(f"   - Total size: {data.get('total_size', total_audio_size)} bytes")
                        break
                        
                    elif data["type"] == "error":
                        print(f"❌ TTS error: {data.get('error')}")
                        break
                        
            except websockets.exceptions.ConnectionClosed:
                print("🔌 WebSocket connection closed")
                
    except Exception as e:
        print(f"❌ WebSocket test failed: {e}")

async def test_direct_service_call():
    """Test direct TTS service call (internal monolith usage)"""
    print("Testing Direct TTS Service Call...\n")
    
    try:
        from app.services.tts_service import tts_service
        
        text = "This is a direct call to the TTS service from within the monolith!"
        print(f"🔊 Testing direct service call: '{text}'")
        
        # Test direct async call
        audio_data = await tts_service.generate_speech(
            text=text,
            speech_type="direct_test"
        )
        
        if audio_data:
            print(f"✅ Direct service call completed: {len(audio_data)} bytes")
            
            # Save audio to file
            with open("direct_tts_output.mp3", "wb") as f:
                f.write(audio_data)
            print(f"   - Audio saved to: direct_tts_output.mp3")
        else:
            print("❌ Direct service call failed")
        
    except Exception as e:
        print(f"❌ Direct service call failed: {e}")

async def main():
    """Run all TTS tests"""
    print("🔊 TTS Service Testing Suite")
    print("=" * 50)
    
    # Test 1: Health check
    test_tts_health()
    print()
    
    # Test 2: Configuration check
    test_tts_config()
    print()
    
    # Test 3: HTTP endpoint
    print("Test 3: HTTP TTS Generation")
    test_tts_http()
    print()
    
    # Test 4: WebSocket interface
    print("Test 4: WebSocket TTS Streaming")
    await test_tts_websocket()
    print()
    
    # Test 5: Direct service call
    print("Test 5: Direct Service Call")
    print("Note: Direct service call test requires the app to be running.")
    print("You can test direct calls from within the application.\n")
    
    print("🎉 TTS testing complete!")
    print("\nGenerated files:")
    print("- test_tts_output.mp3 (from HTTP test)")
    print("- direct_tts_output.mp3 (from direct call test)")

if __name__ == "__main__":
    asyncio.run(main())