from fastapi import APIRouter, WebSocket, Depends, WebSocketDisconnect, Query
from session_engine.engine.websocket_engine import WebSocketInterviewSession
from session_engine.services.tts_handler import TTSHandler
import jwt
from jwt import ExpiredSignatureError, PyJWTError
from auth_service.app.core import config

router = APIRouter()
active_sessions = set()  # ← ADD THIS BACK

@router.websocket("/ws/interview")
async def websocket_interview(websocket: WebSocket, token: str = Query(...)):
    # token = websocket.headers.get("authorization")
    print(f"WebSocket connection attempt with token: {token}")
    if not token:
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
    
    # ← ADD THIS BACK - Session deduplication
    if not user_id in active_sessions:
        active_sessions.add(user_id)
        print(f"🔍 [DEBUG] Added user {user_id} to active sessions. Total: {len(active_sessions)}")
    else:
        print(f"🚨 [DEBUG] User {user_id} already has active session. Rejecting.")
        await websocket.accept()
        await websocket.send_json({
            "type": "terminate",
            "reason": "You already have an active interview session."
        })
        await websocket.close()
        return
    
    await websocket.accept()
    
    # 🔊 Inject TTSHandler
    tts_handler = TTSHandler()
    session = WebSocketInterviewSession(user_id=user_id, websocket=websocket, tts_handler=tts_handler)
    
    try:
        await session.start()
    except WebSocketDisconnect:
        print("Client disconnected")
    finally:  # ← ADD THIS BACK - Session cleanup
        print(f"🔍 [DEBUG] Removing user {user_id} from active sessions")
        active_sessions.discard(user_id)
        print(f"🔍 [DEBUG] Active sessions remaining: {len(active_sessions)}")