from fastapi import FastAPI
from app.schemas.moderation import ModerationRequest, ModerationResponse
from app.services.moderation_service import Moderator

app = FastAPI()
moderator = Moderator()

@app.post("/moderate", response_model=ModerationResponse)
def moderate_input(req: ModerationRequest):
    result = moderator.moderate(req.question, req.user_input)
    return ModerationResponse(status=result.status)
