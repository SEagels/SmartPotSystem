# FastAPI依赖注入层 —— 认证链 + 资源归属验证
# 设计：get_current_device 依赖 get_current_user，形成两层级联依赖：
#   请求 → 解析Token → 查用户 → 查设备归属 → 返回设备（确保用户只能操作自己的设备）
# 这种依赖链条是FastAPI推荐的安全模式：在依赖层完成认证，业务层只处理已验证的资源
from __future__ import annotations

import logging
import uuid
from collections.abc import AsyncGenerator

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.device import Device
from app.models.user import User

logger = logging.getLogger(__name__)


async def get_current_user(
    authorization: str = Header(..., description="Bearer <token>"),
    db: AsyncSession = Depends(get_db),
) -> User:
    """从Authorization头提取JWT → 解析用户ID → 查数据库验证用户存在"""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="未认证")
    token = authorization[7:]
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token无效或已过期")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Token无效")
    # UUID格式校验：防止注入非法格式的user_id
    try:
        uid = uuid.UUID(user_id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=401, detail="Token无效")
    result = await db.execute(select(User).where(User.id == uid))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    return user


async def get_current_device(
    device_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),  # ← 级联依赖：先认证用户
) -> Device:
    """级联依赖：先获取当前用户，再验证device_id属于该用户（防止越权访问其他用户的设备）"""
    result = await db.execute(
        select(Device).where(Device.device_id == device_id, Device.user_id == user.id)
    )
    device = result.scalar_one_or_none()
    if not device:
        raise HTTPException(status_code=404, detail="设备不存在")
    return device
