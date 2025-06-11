import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from fastapi import FastAPI
from session_engine.app.api.routes import router as session_router

app = FastAPI(title="Session Engine")

app.include_router(session_router, prefix="/session")
