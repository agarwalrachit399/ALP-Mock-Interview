from fastapi import APIRouter, Depends
from auth_service.app.services.dependencies import get_current_user
from session_engine.engine.turn_engine import TurnEngine

router = APIRouter()

@router.post("/start")
def start_interview(user=Depends(get_current_user)):
    engine = TurnEngine(user_id=user["id"])
    engine.start_interview()
    return {"message": f"Interview started for user {user['email']}"}
