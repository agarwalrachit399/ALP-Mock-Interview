import os
from dotenv import load_dotenv

load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET", "secret123")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_MINUTES = 60
