from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password, verify_password
from app.models.device import Device
from app.models.user import User


async def register(db: AsyncSession, username: str, password: str, phone: str | None) -> tuple[User, str]:
    result = await db.execute(select(User).where(User.username == username))
    if result.scalar_one_or_none():
        raise ValueError("用户名已存在")
    user = User(username=username, password_hash=hash_password(password), phone=phone)
    db.add(user)
    await db.flush()
    token = create_access_token(str(user.id))
    return user, token


async def login(db: AsyncSession, username: str, password: str) -> tuple[User, str]:
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(password, user.password_hash):
        raise ValueError("用户名或密码错误")
    token = create_access_token(str(user.id))
    return user, token


async def get_profile(db: AsyncSession, user_id: str) -> dict:
    import uuid
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise ValueError("用户不存在")
    count_result = await db.execute(
        select(func.count(Device.device_id)).where(Device.user_id == user.id)
    )
    device_count = count_result.scalar() or 0
    phone = user.phone
    masked = phone[:3] + "****" + phone[-4:] if phone and len(phone) >= 7 else phone
    return {
        "user_id": str(user.id),
        "username": user.username,
        "phone": masked,
        "created_at": user.created_at.strftime("%Y-%m-%dT%H:%M:%SZ") if user.created_at else "",
        "device_count": device_count,
    }
