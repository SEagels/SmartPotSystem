from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.services import auth_service

router = APIRouter(prefix="/auth")


class RegisterBody(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=6, max_length=128)
    phone: str | None = None


class LoginBody(BaseModel):
    username: str
    password: str


@router.post("/register")
async def register(body: RegisterBody, db: AsyncSession = Depends(get_db)):
    try:
        user, token = await auth_service.register(db, body.username, body.password, body.phone)
        return {
            "code": 0, "message": "success",
            "data": {"user_id": str(user.id), "username": user.username, "token": token},
        }
    except ValueError as e:
        return {"code": 1001, "message": str(e), "data": None}


@router.post("/login")
async def login(body: LoginBody, db: AsyncSession = Depends(get_db)):
    try:
        user, token = await auth_service.login(db, body.username, body.password)
        return {
            "code": 0, "message": "success",
            "data": {"user_id": str(user.id), "username": user.username, "token": token},
        }
    except ValueError as e:
        return {"code": 1001, "message": str(e), "data": None}


@router.get("/profile")
async def profile(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    profile_data = await auth_service.get_profile(db, str(user.id))
    return {"code": 0, "message": "success", "data": profile_data}
