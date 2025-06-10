import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    ENV: str = os.getenv("ENV", "dev")
    MONGO_URI: str = os.getenv("MONGO_URI", "")

    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY","")
    

settings = Settings()

