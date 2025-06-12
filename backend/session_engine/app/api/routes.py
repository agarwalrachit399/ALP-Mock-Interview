from fastapi import APIRouter, Depends
from auth_service.app.services.dependencies import get_current_user
from session_engine.engine.turn_engine import TurnEngine
from fastapi import APIRouter, WebSocket, Depends, WebSocketDisconnect
from session_engine.engine.websocket_engine import WebSocketInterviewSession
from session_engine.services.tts_handler import TTSHandler
import jwt
from jwt import ExpiredSignatureError, PyJWTError

from auth_service.app.core import config

router = APIRouter()
active_sessions = set()

@router.post("/start")
def start_interview(user=Depends(get_current_user)):
    engine = TurnEngine(user_id=user["id"])
    engine.start_interview()
    return {"message": f"Interview started for user {user['email']}"}



@router.websocket("/ws/interview")
async def websocket_interview(websocket: WebSocket):
    token = websocket.headers.get("authorization")
    print(f"WebSocket connection attempt with token: {token}")
    if not token or not token.startswith("Bearer "):
        await websocket.close(code=403)
        return

    try:
        jwt_token = token.replace("Bearer ", "")
        payload = jwt.decode(jwt_token, config.JWT_SECRET, algorithms=[config.JWT_ALGORITHM])
        user_id = payload.get("user_id")
        print(f"Decoded user_id: {user_id}")
        if not user_id:
            await websocket.close(code=403)
            return
    except (ExpiredSignatureError, PyJWTError):
        await websocket.close(code=403)
        return
    
    if user_id in active_sessions:
        await websocket.accept()
        await websocket.send_json({
            "type": "terminate",
            "reason": "You already have an active interview session."
        })
        await websocket.close()
        return

    active_sessions.add(user_id)

    await websocket.accept()

    # 🔊 Inject TTSHandler
    tts_handler = TTSHandler()
    session = WebSocketInterviewSession(user_id=user_id, websocket=websocket, tts_handler=tts_handler)

    try:
        await session.start()
    except WebSocketDisconnect:
        print("Client disconnected")
