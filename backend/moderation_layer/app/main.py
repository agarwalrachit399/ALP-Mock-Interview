from fastapi import FastAPI, HTTPException
from schema import ModerationRequest, ModerationResponse
from moderator import Moderator

app = FastAPI()
moderator = Moderator()



@app.post("/moderate", response_model=ModerationResponse)
def moderate_input(req: ModerationRequest):
    result = moderator.moderate(req.user_input)
    return ModerationResponse(status=result.status)