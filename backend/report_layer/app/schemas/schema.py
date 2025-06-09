from pydantic import BaseModel
from typing import List

class ReportRequest(BaseModel):
    user_id: str
    conversation: List[str]  # Or List[dict] if structured

class ReportResponse(BaseModel):
    summary: str
    score: float
