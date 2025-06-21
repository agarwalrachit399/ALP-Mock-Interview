from fastapi import APIRouter, HTTPException
from app.models.followup import (
    FollowupRequest, 
    ShouldGenerateRequest, 
    SessionCleanupRequest, 
    SessionCleanupResponse,
    FollowupResponse,
    ShouldFollowupResponse
)
from app.services.followup_service import followup_service
from app.services.session_memory import session_memory_manager

router = APIRouter()

@router.post("/generate-followup", response_model=FollowupResponse)
async def generate_followup(data: FollowupRequest):
    """Generate a followup question"""
    try:
        followup = followup_service.generate_followup(data)
        return FollowupResponse(followup=followup)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/should-followup", response_model=ShouldFollowupResponse)
async def should_followup(data: ShouldGenerateRequest):
    """Determine if a followup question should be asked"""
    try:
        result = followup_service.should_generate_followup(data)
        return ShouldFollowupResponse(followup=result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/cleanup-session", response_model=SessionCleanupResponse)
async def cleanup_session(data: SessionCleanupRequest):
    """Clean up a specific session to free memory"""
    try:
        success = session_memory_manager.cleanup_session(data.session_id)
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
        cleaned_count = session_memory_manager.cleanup_expired_sessions()
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
        stats = session_memory_manager.get_memory_stats()
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
        details = session_memory_manager.get_session_details(session_id)
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
        cleaned_count = session_memory_manager.force_cleanup_all()
        return {
            "success": True,
            "message": f"Force cleaned {cleaned_count} sessions"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Error during force cleanup: {str(e)}"
        }