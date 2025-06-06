from pydantic import BaseModel

class ModerationRequest(BaseModel):
    user_input: str

class ModerationResponse(BaseModel):
    status : str