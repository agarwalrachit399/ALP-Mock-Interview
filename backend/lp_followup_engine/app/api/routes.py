from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from app.schemas.requests import FollowupRequest, ShouldGenerateRequest, SessionCleanupRequest, SessionCleanupResponse
from app.db.session_memory import SessionMemoryManager
from app.services.followup_generator import FollowupGenerator
from app.services.followup_decider import FollowupDecider

router = APIRouter()
memory_manager = SessionMemoryManager()
generator = FollowupGenerator()
decider = FollowupDecider()

@router.post("/generate-followup")
async def generate_followup(data: FollowupRequest):
    try:
        session_id, principle, question, user_input = data.session_id, data.principle, data.question, data.user_input

        if not memory_manager.has_session(session_id, principle):
            memory_manager.start_lp(session_id, principle, question, user_input)
        else:
            memory_manager.add_followup(session_id, principle, question, user_input)

        history = memory_manager.get_history(session_id, principle)
        stream = generator.generate(principle, history)
        # return StreamingResponse(stream, media_type="text/plain")
        return {"followup": stream}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/should-followup")
async def should_followup(data: ShouldGenerateRequest):
    try:
        if not memory_manager.has_session(data.session_id, data.principle):
            memory_manager.start_lp(data.session_id, data.principle, data.question, data.user_input)
        else:
            memory_manager.add_followup(data.session_id, data.principle, data.question, data.user_input)

        history = memory_manager.get_history(data.session_id, data.principle)
        result = decider.decide(
            data.principle,
            data.time_remaining,
            data.num_lp_questions,
            history,
            data.time_spent,
            data.num_followups
        )
        return {"followup": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/cleanup-session", response_model=SessionCleanupResponse)
async def cleanup_session(data: SessionCleanupRequest):
    """Clean up a specific session to free memory"""
    try:
        success = memory_manager.cleanup_session(data.session_id)
        if success:
            return SessionCleanupResponse(
                success=True,
                message=f"Session {data.session_id} cleaned up successfully"
            )
        else:
            return SessionCleanupResponse(
                success=False,
                message=f"Session {data.session_id} not found"
            )
    except Exception as e:
        return SessionCleanupResponse(
            success=False,
            message=f"Error cleaning up session: {str(e)}"
        )

@router.post("/cleanup-expired")
async def cleanup_expired_sessions():
    """Clean up all expired sessions"""
    try:
        cleaned_count = memory_manager.cleanup_expired_sessions()
        return {
            "success": True,
            "message": f"Cleaned up {cleaned_count} expired sessions"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error during cleanup: {str(e)}"
        }

@router.get("/memory-stats")
async def get_memory_stats():
    """Get current memory usage statistics"""
    try:
        stats = memory_manager.get_memory_stats()
        return {
            "success": True,
            "stats": stats
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error getting memory stats: {str(e)}"
        }

@router.get("/session-details/{session_id}")
async def get_session_details(session_id: str):
    """Get detailed information about a specific session"""
    try:
        details = memory_manager.get_session_details(session_id)
        if details:
            return {
                "success": True,
                "details": details
            }
        else:
            return {
                "success": False,
                "message": f"Session {session_id} not found"
            }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error getting session details: {str(e)}"
        }

@router.post("/force-cleanup-all")
async def force_cleanup_all():
    """Emergency endpoint to clean up all sessions"""
    try:
        cleaned_count = memory_manager.force_cleanup_all()
        return {
            "success": True,
            "message": f"Force cleaned {cleaned_count} sessions"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error during force cleanup: {str(e)}"
        }