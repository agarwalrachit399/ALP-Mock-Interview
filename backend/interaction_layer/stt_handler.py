import os
import asyncio
import time
import numpy as np
import pyaudio
from dotenv import load_dotenv
import speechmatics
from speechmatics.models import (
    ConnectionSettings,
    TranscriptionConfig,
    AudioSettings,
    ServerMessageType,
)
from httpx import HTTPStatusError

load_dotenv()

API_KEY = os.getenv("SPEECHMATICS_API_KEY")
LANGUAGE = "en"
CONNECTION_URL = f"wss://eu2.rt.speechmatics.com/v2/{LANGUAGE}"
CHUNK_SIZE = 1024


class AudioProcessor:
    def __init__(self):
        self.wave_data = bytearray()
        self.read_offset = 0
        self.finished = False
    
    def finish(self):
        self.finished = True


    async def read(self, chunk_size):
        while self.read_offset + chunk_size > len(self.wave_data):
            if self.finished:
                return b""  # Signal end-of-audio
            await asyncio.sleep(0.001)

        new_offset = self.read_offset + chunk_size
        data = self.wave_data[self.read_offset:new_offset]
        self.read_offset = new_offset
        return data


    def write_audio(self, data):
        self.wave_data.extend(data)


class STTTranscriber:
    def __init__(self):
        self.audio_processor = AudioProcessor()
        self.transcript_final = ""
        self.last_voice_time = time.time()
        self.silence_threshold = 0.01  # Adjust if needed
        self.silence_duration = 2.0    # seconds
        self.silence_started = None
        self.stop_transcription = False
        self.ws = None  # to be set later
        


    def stream_callback(self, in_data, frame_count, time_info, status):
        if self.stop_transcription:
            print("🔁 Stream callback returning silence to finish...")
            self.audio_processor.finish()
            return (bytes(len(in_data)), pyaudio.paComplete)

        self.audio_processor.write_audio(in_data)

        # Volume detection
        audio_np = np.frombuffer(in_data, dtype=np.float32)
        volume = np.sqrt(np.mean(audio_np ** 2))

        if volume > self.silence_threshold:
            self.last_voice_time = time.time()
            self.silence_started = None
        elif time.time() - self.last_voice_time > self.silence_duration:
            if self.silence_started is None:
                self.silence_started = time.time()
            elif time.time() - self.silence_started > 0.5:
                print("🛑 Sustained silence. Preparing to stop...")
                self.stop_transcription = True

        return in_data, pyaudio.paContinue

    def on_partial(self, msg):
        if 'transcript' in msg['metadata']:
            print(f"[partial] {msg['metadata']['transcript']}")

    def on_final(self, msg):
        text = msg['metadata']['transcript']
        self.transcript_final += text + " "
        print(f"[FINAL SAVED] {text}")

    def get_default_device(self):
        p = pyaudio.PyAudio()
        default_index = p.get_default_input_device_info()['index']
        rate = int(p.get_device_info_by_index(default_index)['defaultSampleRate'])
        return default_index, rate

    def get_microphone_stream(self, device_index, sample_rate):
        p = pyaudio.PyAudio()
        return p.open(
            format=pyaudio.paFloat32,
            channels=1,
            rate=sample_rate,
            input=True,
            frames_per_buffer=CHUNK_SIZE,
            input_device_index=device_index,
            stream_callback=self.stream_callback
        )

    def run_transcription(self):
        device_index, sample_rate = self.get_default_device()
        stream = self.get_microphone_stream(device_index, sample_rate)

        conn = ConnectionSettings(url=CONNECTION_URL, auth_token=API_KEY)
        self.ws = speechmatics.client.WebsocketClient(conn)

        conf = TranscriptionConfig(
            language=LANGUAGE,
            enable_partials=True,
            max_delay=5,
        )

        audio_settings = AudioSettings(
            encoding="pcm_f32le",
            sample_rate=sample_rate,
            chunk_size=CHUNK_SIZE,
        )

        # Register event handlers
        self.ws.add_event_handler(ServerMessageType.AddPartialTranscript, self.on_partial)
        self.ws.add_event_handler(ServerMessageType.AddTranscript, self.on_final)

        print("🎤 Listening... Speak now (auto-stops on 2s silence)")

        try:
            self.ws.run_synchronously(self.audio_processor, conf, audio_settings)
        except HTTPStatusError as e:
            if e.response.status_code == 401:
                print("Invalid API Key.")
            else:
                raise e

        return self.transcript_final.strip()


def transcribe_speech():
    transcriber = STTTranscriber()
    return transcriber.run_transcription()


if __name__ == "__main__":
    try:
        final_transcript = transcribe_speech()
        print("\n✅ Final Transcript:")
        print(final_transcript)
    except KeyboardInterrupt:
        print("\n🛑 Transcription stopped by user.")
    except Exception as e:  
        print(f"❌ An error occurred: {e}")
        raise e
