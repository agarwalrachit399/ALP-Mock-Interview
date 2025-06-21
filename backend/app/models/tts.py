from pydantic import BaseModel
from typing import Optional, List

class TTSRequest(BaseModel):
    message_id: str
    text: str
    speech_type: str = "system"  # "system", "question", "retry", etc.

class TTSResponse(BaseModel):
    type: str  # "tts_started", "audio_chunk", "tts_complete", "error"
    message_id: str
    chunk: Optional[str] = None  # base64 encoded audio
    format: Optional[str] = None  # "mp3"
    error: Optional[str] = None
    total_size: Optional[int] = None
    total_chunks: Optional[int] = None

class TTSConfig(BaseModel):
    speaker: str = "cove"
    model_id: str = "mistv2"
    audio_format: str = "mp3"

class DirectTTSRequest(BaseModel):
    text: str
    speech_type: str = "system"
    config: Optional[TTSConfig] = None

class DirectTTSResponse(BaseModel):
    success: bool
    audio_data: Optional[str] = None  # base64 encoded
    audio_size: Optional[int] = None
    error: Optional[str] = None