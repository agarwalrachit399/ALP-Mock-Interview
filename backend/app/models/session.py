from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class InterviewConfig(BaseModel):
    session_duration_limit: int = 180  # 3 minutes in seconds
    min_lp_questions: int = 1
    follow_up_count: int = 2

class SessionMessage(BaseModel):
    type: str  # "system", "question", "speech", "answer", "complete", "terminate", etc.
    text: Optional[str] = None
    message_id: Optional[str] = None
    session_id: Optional[str] = None
    speech_type: Optional[str] = None
    error: Optional[str] = None
    reason: Optional[str] = None
    has_rime_audio: Optional[bool] = None
    # Audio-related fields for TTS coordination
    chunk: Optional[str] = None
    format: Optional[str] = None
    total_chunks: Optional[int] = None
    timestamp: Optional[float] = None

class AudioPlaybackMessage(BaseModel):
    type: str  # "tts_started", "tts_completed", "audio_playback_started", etc.
    message_id: str
    error: Optional[str] = None

class SessionStats(BaseModel):
    session_id: str
    user_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    lp_questions_asked: int = 0
    total_followups: int = 0
    status: str = "active"  # "active", "completed", "terminated", "error"

class InterviewSession(BaseModel):
    session_id: str
    user_id: str
    config: InterviewConfig
    stats: SessionStats
    active_lp: Optional[str] = None
    current_question: Optional[str] = None
    pending_questions: Dict[str, Any] = {}
    tts_events: Dict[str, Any] = {}