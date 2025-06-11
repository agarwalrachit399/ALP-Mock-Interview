from fastapi import APIRouter, HTTPException, Depends
from app.models.user_model import UserCreate, UserLogin, UserOut
from app.services.auth import AuthService
from app.db.user_handler import UserDB

router = APIRouter()

@router.post("/signup", response_model=UserOut)
async def signup(user: UserCreate):
    return await AuthService.signup(user)

@router.post("/login")
async def login(user: UserLogin):
    return await AuthService.login(user)
