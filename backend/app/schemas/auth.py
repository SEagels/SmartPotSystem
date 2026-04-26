from __future__ import annotations

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=128)
    phone: str | None = Field(default=None, max_length=20)


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenData(BaseModel):
    user_id: str
    username: str
    token: str
    expires_at: str


class ProfileData(BaseModel):
    user_id: str
    username: str
    phone: str | None = None
    created_at: str
    device_count: int = 0
