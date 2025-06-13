from pydantic import BaseModel
from typing import List
from pydantic import BaseModel
from typing import List, Literal

class SessionIDRequest(BaseModel):
    session_id: str
    
class ReportRequest(BaseModel):
    user_id: str
    conversation: List[str]  # or List[dict] if detailed turns
    # intended_lp: str  # new: specify the primary LP you're targeting

class STARFormat(BaseModel):
    situation: bool
    task: bool
    action: bool
    result: bool
    comment: str

class AnswerQuality(BaseModel):
    relevance: bool
    conciseness: bool
    on_track: bool
    realism: bool
    followups_handled_well: bool
    comment: str

class ReportResponse(BaseModel):
    # intended_lp: str
    # lp_demonstrated: str
    other_lps_mentioned: List[str]
    star_format: STARFormat
    answer_quality: AnswerQuality
    score: float
    positives: List[str]
    improvements_needed: List[str]
