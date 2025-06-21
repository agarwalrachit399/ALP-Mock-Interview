from fastapi import APIRouter
from app.models.moderation import ModerationRequest, ModerationResponse
from app.services.moderation_service import ModerationService

router = APIRouter()
moderator = ModerationService()

@router.post("/moderate", response_model=ModerationResponse)
def moderate_input(req: ModerationRequest):
    result = moderator.moderate(req.question, req.user_input)
    return result