import os
from dotenv import load_dotenv
from speechmatics.models import ConnectionSettings
from speechmatics.batch_client import BatchClient
from httpx import HTTPStatusError

load_dotenv()

SPEECH_API_KEY = os.getenv("SPEECHMATICS_API_KEY")
LANGUAGE = "en"
AUDIO_PATH = "input_audio.wav"

settings = ConnectionSettings(
    url="https://asr.api.speechmatics.com/v2",
    auth_token=SPEECH_API_KEY,
)


# Define transcription parameters
conf = {
    "type": "transcription",
    "transcription_config": {
        "language": LANGUAGE
    }
}

def transcribe_speech():
    """
    Capture audio and send it to Speechmatics STT API.
    This is a placeholder function. Integrate streaming or file-based STT as needed.
    """
    with BatchClient(settings) as client:
        try:
            job_id = client.submit_job(
                audio=AUDIO_PATH,
                transcription_config=conf,
            )
            print(f'job {job_id} submitted successfully, waiting for transcript')

            # Note that in production, you should set up notifications instead of polling.
            # Notifications are described here: https://docs.speechmatics.com/features-other/notifications
            transcript = client.wait_for_completion(job_id, transcription_format='txt')
            # To see the full output, try setting transcription_format='json-v2'.
            print(transcript)
        except HTTPStatusError as e:
            if e.response.status_code == 401:
                print('Invalid API key - Check your API_KEY at the top of the code!')
            elif e.response.status_code == 400:
                print(e.response.json()['detail'])
            else:
                raise e
    
    # TODO: integrate Speechmatics streaming or upload logic here
    return "This is a placeholder transcription."


