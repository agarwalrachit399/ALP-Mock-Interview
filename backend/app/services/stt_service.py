import os
import asyncio
import time
import numpy as np
import pyaudio
import speechmatics
from speechmatics.models import (
    ConnectionSettings,
    TranscriptionConfig,
    AudioSettings,
    ServerMessageType,
)
from httpx import HTTPStatusError
import webrtcvad
import threading
from typing import Optional
from app.core.config import settings

CHUNK_SIZE = 960  # 30ms at 16kHz with 16-bit PCM (960 bytes)

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

class VADMonitor:
    def __init__(self, sample_rate=16000):
        self.vad = webrtcvad.Vad(3)
        self.sample_rate = sample_rate
        self.silence_start_time = None
        self.speech_detected = False

    def update(self, pcm_data):
        try:
            is_speech = self.vad.is_speech(pcm_data, self.sample_rate)
        except webrtcvad.VadError:
            is_speech = False

        if is_speech:
            print("🗣️ Speech detected")
            self.speech_detected = True
            self.silence_start_time = None
        else:
            if self.speech_detected and self.silence_start_time is None:
                self.silence_start_time = time.time()

    def is_sustained_silence(self, duration):
        return self.silence_start_time and (time.time() - self.silence_start_time) >= duration

class STTTranscriber:
    def __init__(self, silence_duration, max_wait=None, cancel_event=None):
        self.silence_duration = silence_duration
        self.max_wait = max_wait
        self.cancel_event = cancel_event
        self.audio_processor = AudioProcessor()
        self.transcript_final = ""
        self.vad_monitor = VADMonitor()
        self.stop_transcription = False
        self.ws = None
        self.sample_rate = 16000
        self.start_time = time.time()

    def stream_callback(self, in_data, frame_count, time_info, status):
        # Check cancel signal
        if self.cancel_event and self.cancel_event.is_set():
            print("❌ Cancel signal received from cancellation event.")
            self.stop_transcription = True

        # Check max wait if no speech yet
        if not self.vad_monitor.speech_detected:
            if not hasattr(self, "no_speech_start_time"):
                self.no_speech_start_time = time.time()

            if self.max_wait and (time.time() - self.no_speech_start_time > self.max_wait):
                print("⏰ No speech detected for max_wait duration. Ending.")
                self.stop_transcription = True
        else:
            # Reset no speech timer
            self.no_speech_start_time = None

        # Stop if triggered
        if self.stop_transcription:
            print("🔁 Stream callback returning silence to finish...")
            self.audio_processor.finish()
            return (bytes(len(in_data)), pyaudio.paComplete)

        self.audio_processor.write_audio(in_data)

        # Convert and update VAD
        float_audio = np.frombuffer(in_data, dtype=np.float32)
        int16_audio = np.clip(float_audio * 32768, -32768, 32767).astype(np.int16)
        pcm_data = int16_audio.tobytes()

        frame_duration_ms = 30
        frame_size = int(self.sample_rate * frame_duration_ms / 1000) * 2

        if len(pcm_data) >= frame_size:
            frame = pcm_data[:frame_size]
            self.vad_monitor.update(frame)

        if self.vad_monitor.is_sustained_silence(self.silence_duration):
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
        return default_index, self.sample_rate

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
        stream = None
        
        try:
            stream = self.get_microphone_stream(device_index, sample_rate)

            # Use API key from settings
            connection_url = f"wss://eu2.rt.speechmatics.com/v2/en"
            conn = ConnectionSettings(url=connection_url, auth_token=settings.SPEECHMATICS_API_KEY)
            self.ws = speechmatics.client.WebsocketClient(conn)

            conf = TranscriptionConfig(
                language="en",
                enable_partials=True,
                max_delay=5,
            )

            audio_settings = AudioSettings(
                encoding="pcm_f32le",
                sample_rate=sample_rate,
                chunk_size=CHUNK_SIZE,
            )

            self.ws.add_event_handler(ServerMessageType.AddPartialTranscript, self.on_partial)
            self.ws.add_event_handler(ServerMessageType.AddTranscript, self.on_final)

            try:
                self.ws.run_synchronously(self.audio_processor, conf, audio_settings)
            except HTTPStatusError as e:
                if e.response.status_code == 401:
                    print("Invalid Speechmatics API Key.")
                    return ""
                else:
                    raise e
                    
        except Exception as e:
            print(f"STT Transcription error: {e}")
            return ""
        finally:
            # Cleanup resources
            if stream:
                try:
                    stream.stop_stream()
                    stream.close()
                    print("🧹 [STT] PyAudio stream closed")
                except Exception as e:
                    print(f"Error closing audio stream: {e}")
            
            if hasattr(self, 'ws') and self.ws:
                try:
                    # Speechmatics client cleanup (if available)
                    if hasattr(self.ws, 'close'):
                        self.ws.close()
                    print("🧹 [STT] Speechmatics WebSocket closed")
                except Exception as e:
                    print(f"Error closing Speechmatics connection: {e}")

        return self.transcript_final.strip()

class STTService:
    """Speech-to-Text service for the monolith"""
    
    def __init__(self):
        self.active_transcriptions = {}  # Track active transcription sessions
    
    async def transcribe_speech(self, stop_duration: int = 4, max_wait: int = 10, 
                               cancel_event: Optional[threading.Event] = None) -> str:
        """
        Transcribe speech from microphone
        
        Args:
            stop_duration: Seconds of silence before stopping
            max_wait: Maximum seconds to wait for speech
            cancel_event: Threading event to cancel transcription
            
        Returns:
            Transcribed text or empty string if cancelled/failed
        """
        print(f"🎤 [STT] Starting transcription (stop: {stop_duration}s, max_wait: {max_wait}s)")
        
        if not settings.SPEECHMATICS_API_KEY:
            print("❌ [STT] SPEECHMATICS_API_KEY not configured")
            return ""
        
        # Run transcription in executor to avoid blocking
        loop = asyncio.get_event_loop()
        
        try:
            # Create transcriber
            transcriber = STTTranscriber(
                silence_duration=stop_duration,
                max_wait=max_wait,
                cancel_event=cancel_event
            )
            
            # Run transcription in thread pool
            transcript = await loop.run_in_executor(
                None, 
                transcriber.run_transcription
            )
            
            print(f"🎤 [STT] Transcription completed: '{transcript}'")
            return transcript
            
        except Exception as e:
            print(f"❌ [STT] Transcription error: {e}")
            return ""
    
    def transcribe_speech_sync(self, stop_duration: int = 4, max_wait: int = 10, 
                              cancel_event: Optional[threading.Event] = None) -> str:
        """
        Synchronous version of transcribe_speech for use in non-async contexts
        """
        transcriber = STTTranscriber(
            silence_duration=stop_duration,
            max_wait=max_wait,
            cancel_event=cancel_event
        )
        
        return transcriber.run_transcription()

# Global STT service instance
stt_service = STTService()