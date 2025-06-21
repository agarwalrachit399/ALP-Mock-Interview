from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import logging
from contextlib import asynccontextmanager
from app.api import auth, moderation, followup, stt, tts, session
from app.core.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("🚀 Starting AI Interview Platform...")
    await validate_api_connections()
    logger.info("✅ All systems validated - Application ready!")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down AI Interview Platform...")
    # Add any cleanup logic here if needed

app = FastAPI(title="AI Interview Platform", lifespan=lifespan)

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

async def validate_api_connections():
    """Test actual API connectivity"""
    logger.info("🔍 Validating API connections...")
    
    # Test database connection
    try:
        from app.core.database import check_database_health
        if not check_database_health():
            raise Exception("Database connection failed")
        logger.info("✅ Database connection validated")
    except Exception as e:
        logger.error(f"❌ Database validation failed: {e}")
        raise
    
    # Test Gemini API
    try:
        from google import genai
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        # Simple test call
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents="Test",
            config={"max_output_tokens": 10}
        )
        logger.info("✅ Gemini API connection validated")
    except Exception as e:
        logger.error(f"❌ Gemini API validation failed: {e}")
        logger.warning("⚠️ Followup and moderation services may not work")
    
    # Test Speechmatics API (basic format check)
    if not settings.SPEECHMATICS_API_KEY:
        logger.warning("⚠️ Speechmatics API key missing - STT will not work")
    else:
        logger.info("✅ Speechmatics API key present")
    
    # Test Rime API (basic format check)  
    if not settings.RIME_API_KEY:
        logger.warning("⚠️ Rime API key missing - TTS will not work")
    else:
        logger.info("✅ Rime API key present")

# Include routers (unchanged)
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