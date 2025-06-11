from fastapi import APIRouter, HTTPException, Depends
from auth_service.app.models.user_model import UserCreate, UserLogin, UserOut
from auth_service.app.services.auth import AuthService
from auth_service.app.db.user_handler import UserDB

router = APIRouter()

@router.post("/signup", response_model=UserOut)
async def signup(user: UserCreate):
    return await AuthService.signup(user)

@router.post("/login")
async def login(user: UserLogin):
    return await AuthService.login(user)
