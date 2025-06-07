from pydantic import BaseModel

class ModerationRequest(BaseModel):
    question: str
    user_input: str

class ModerationResponse(BaseModel):
    status : str