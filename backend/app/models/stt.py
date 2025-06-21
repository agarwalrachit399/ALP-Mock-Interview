from pydantic import BaseModel
from typing import Optional

class STTConfig(BaseModel):
    stop_duration: int = 4
    max_wait: int = 10

class STTResponse(BaseModel):
    type: str  # "done", "cancelled", "error"
    text: Optional[str] = None
    message: Optional[str] = None

class STTRequest(BaseModel):
    config: STTConfig
    command: Optional[str] = None  # "cancel" for cancellation