from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from app.schemas.requests import FollowupRequest, ShouldGenerateRequest
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
        # stream = generator.generate(principle, history)
        # return StreamingResponse(stream, media_type="text/plain")
        followup = generator.generate(principle, history)
        
        return {"followup": followup}

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
