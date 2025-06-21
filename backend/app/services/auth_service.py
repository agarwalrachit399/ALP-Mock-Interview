from passlib.context import CryptContext
from datetime import datetime, timedelta
import jwt
from fastapi import HTTPException
from app.core.config import settings
from app.models.user import UserCreate, UserLogin
from app.core.database import UserDB

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthService:
    
    @staticmethod
    def hash_password(password: str) -> str:
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def create_token(user_id: str, email: str) -> str:
        payload = {
            "user_id": user_id,
            "email": email,
            "exp": datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRY_MINUTES)
        }
        return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

    @staticmethod
    async def signup(user: UserCreate):
        existing = UserDB.get_user_by_email(user.email)
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")

        hashed_pw = AuthService.hash_password(user.password)
        user_doc = UserDB.create_user(user.name, user.email, hashed_pw)
        token = AuthService.create_token(str(user_doc["_id"]), user.email)

        return {
            "id": str(user_doc["_id"]),
            "name": user_doc["name"],
            "email": user_doc["email"],
            "created_at": user_doc["created_at"],
            "token": token
        }

    @staticmethod
    async def login(user: UserLogin):
        user_doc = UserDB.get_user_by_email(user.email)
        if not user_doc:
            raise HTTPException(status_code=404, detail="User not found")

        if not AuthService.verify_password(user.password, user_doc["hashed_password"]):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        token = AuthService.create_token(str(user_doc["_id"]), user.email)
        return {
            "token": token
        }