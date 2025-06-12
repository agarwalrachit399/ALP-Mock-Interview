import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
from fastapi import FastAPI
from session_engine.app.api.routes import router as session_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Session Engine")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ⬅️ this is critical
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(session_router, prefix="/session")
