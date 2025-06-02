from stt_handler import transcribe_speech
from mock_llm import generate_response
from tts_handler import speak_response

def run_mock_interview():
    print("🎤 Listening for candidate response...")
    user_text = transcribe_speech()

    print(f"🗣️ Transcription: {user_text}")
    response_text = generate_response(user_text)
    
    print(f"🤖 Bot Response: {response_text}")
    speak_response(response_text)

if __name__ == "__main__":
    run_mock_interview()
