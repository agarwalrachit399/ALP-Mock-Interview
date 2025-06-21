from pydantic import BaseModel

class FollowupRequest(BaseModel):
    session_id: str
    principle: str
    question: str
    user_input: str

class ShouldGenerateRequest(BaseModel):
    session_id: str
    principle: str
    question: str
    user_input: str
    time_remaining: int
    time_spent: int
    num_followups: int
    num_lp_questions: int

class SessionCleanupRequest(BaseModel):
    session_id: str

class SessionCleanupResponse(BaseModel):
    success: bool
    message: str

class FollowupResponse(BaseModel):
    followup: str

class ShouldFollowupResponse(BaseModel):
    followup: bool