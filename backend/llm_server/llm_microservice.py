import sys
import os
sys.path.append(os.path.dirname(__file__))

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
from llm_client import LLMClient
from session_memory_manager import SessionMemoryManager

app = FastAPI()
llm_client = LLMClient()
memory_manager = SessionMemoryManager()

class FollowupRequest(BaseModel):
    session_id: str
    principle: str
    question: str  # Main LP question
    user_input: str  # Response to either main or follow-up

@app.post("/generate-followup")
async def generate_followup(data: FollowupRequest):
    try:
        session_id = data.session_id
        principle = data.principle
        question = data.question
        user_input = data.user_input

        if not memory_manager.has_session(session_id, principle):
            memory_manager.start_lp(session_id, principle, question, user_input)
        else:
            memory_manager.add_followup(session_id, principle, question, user_input)

        history = memory_manager.get_history(session_id, principle)
        followup = llm_client.generate_followup(principle, history)

        return {"followup_question": followup}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM generation failed: {str(e)}")