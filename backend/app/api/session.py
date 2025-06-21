from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, HTTPException
import jwt
from jwt import ExpiredSignatureError, PyJWTError
import logging
from app.core.config import settings
from app.services.session_service import InterviewSessionService, active_sessions

router = APIRouter()
logger = logging.getLogger(__name__)

@router.websocket("/ws/interview")
async def websocket_interview(websocket: WebSocket, token: str = Query(...)):
    """
    Main WebSocket endpoint for interview sessions
    This replaces the entire session_engine microservice
    """
    logger.info(f"🔗 [WEBSOCKET] Connection attempt with token: {token[:20]}...")
    
    if not token:
        await websocket.close(code=403)
        return
    
    # Validate JWT token
    try:
        jwt_token = token.replace("Bearer ", "")
        payload = jwt.decode(jwt_token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        user_id = payload.get("user_id")
        logger.info(f"✅ [AUTH] Authenticated user: {user_id}")
        
        if not user_id:
            await websocket.close(code=403)
            return
            
    except (ExpiredSignatureError, PyJWTError) as e:
        logger.warning(f"❌ [AUTH] Invalid token: {e}")
        await websocket.close(code=403)
        return
    
    # Session deduplication - prevent multiple sessions per user
    if user_id in active_sessions:
        logger.warning(f"🚨 [SESSION] User {user_id} already has active session")
        await websocket.accept()
        await websocket.send_json({
            "type": "terminate",
            "reason": "You already have an active interview session."
        })
        await websocket.close()
        return
    
    # Accept WebSocket connection
    await websocket.accept()
    logger.info(f"✅ [WEBSOCKET] Connection accepted for user {user_id}")
    
    # Add to active sessions
    active_sessions.add(user_id)
    logger.info(f"📊 [SESSIONS] Active sessions: {len(active_sessions)}")
    
    try:
        # Create and start interview session
        session_service = InterviewSessionService(user_id=user_id, websocket=websocket)
        
        logger.info(f"🎭 [INTERVIEW] Starting session for user {user_id}")
        await session_service.start_interview()
        
    except WebSocketDisconnect:
        logger.info(f"🔌 [WEBSOCKET] Client {user_id} disconnected normally")
    except Exception as e:
        logger.error(f"❌ [SESSION] Session error for user {user_id}: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Session cleanup
        active_sessions.discard(user_id)
        logger.info(f"🧹 [CLEANUP] Removed user {user_id} from active sessions")
        logger.info(f"📊 [SESSIONS] Active sessions remaining: {len(active_sessions)}")
        logger.info(f"🎭 [INTERVIEW] Session ended for user {user_id}")

@router.get("/health")
async def session_health_check():
    """Health check for session service"""
    return {
        "status": "healthy",
        "service": "session",
        "active_sessions": len(active_sessions),
        "services_integrated": {
            "auth": True,
            "moderation": True, 
            "followup": True,
            "stt": True,
            "tts": True
        }
    }

@router.get("/stats")
async def session_stats():
    """Get session statistics"""
    return {
        "active_sessions": len(active_sessions),
        "session_config": {
            "duration_limit_seconds": settings.SESSION_DURATION_LIMIT,
            "min_lp_questions": settings.MIN_LP_QUESTIONS,
            "follow_up_count": settings.FOLLOW_UP_COUNT
        },
        "integrated_services": [
            "auth_service",
            "moderation_service", 
            "followup_service",
            "stt_service",
            "tts_service",
            "session_memory"
        ]
    }

@router.post("/terminate/{user_id}")
async def terminate_user_session(user_id: str):
    """Administrative endpoint to terminate a user's session"""
    if user_id in active_sessions:
        active_sessions.discard(user_id)
        return {
            "success": True,
            "message": f"Session for user {user_id} has been terminated"
        }
    else:
        raise HTTPException(
            status_code=404, 
            detail=f"No active session found for user {user_id}"
        )