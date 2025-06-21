from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth, moderation, followup, stt, tts, session

app = FastAPI(title="AI Interview Platform")

# CORS middleware
origins = [
    "http://localhost:5173",  # Vite dev server
    "http://localhost:3000",  # React dev server
    # Add production domain when deployed
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(moderation.router, prefix="/moderation", tags=["Moderation"])
app.include_router(followup.router, prefix="/followup", tags=["Followup"])
app.include_router(stt.router, prefix="/stt", tags=["Speech-to-Text"])
app.include_router(tts.router, prefix="/tts", tags=["Text-to-Speech"])
app.include_router(session.router, prefix="/session", tags=["Interview Sessions"])

@app.get("/")
async def root():
    return {"message": "AI Interview Platform API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "monolith"}