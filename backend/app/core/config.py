import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    # Database
    MONGO_URI: str = os.getenv("MONGO_URI")
    
    # API Keys
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY")
    SPEECHMATICS_API_KEY: str = os.getenv("SPEECHMATICS_API_KEY")
    RIME_API_KEY: str = os.getenv("RIME_API_KEY")
    
    # JWT Configuration
    JWT_SECRET: str = os.getenv("JWT_SECRET_KEY")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_MINUTES: int = 60
    
    # Session Configuration
    SESSION_DURATION_LIMIT: int = 30 * 60  # in seconds
    MIN_LP_QUESTIONS: int = 1
    FOLLOW_UP_COUNT: int = 2

settings = Settings()