# JWT认证 + bcrypt密码哈希 —— 无状态认证核心
# 设计：JWT不存黑名单（无状态），过期后客户端主动刷新；bcrypt自动加盐防止彩虹表攻击
# jti字段为每个Token分配唯一ID，为后续Token撤销/审计预留扩展点
from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

# 抑制 passlib 与 bcrypt 4.x 的兼容性警告
logging.getLogger("passlib").setLevel(logging.ERROR)

# CryptContext：统一密码哈希策略，自动处理salt生成和版本升级
_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__truncate_error=False)


def hash_password(plain: str) -> str:
    """bcrypt哈希密码，自动加盐"""
    return _pwd_ctx.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """验证密码：从哈希值中提取salt后重新计算比对"""
    return _pwd_ctx.verify(plain, hashed)


def create_access_token(user_id: str, expires_delta: timedelta | None = None) -> str:
    """签发JWT Token：sub存用户ID，jti存唯一标识用于审计追踪"""
    now = datetime.now(UTC)
    expire = now + (expires_delta or timedelta(minutes=settings.JWT_EXPIRE_MINUTES))
    payload = {"sub": user_id, "iat": now, "exp": expire, "jti": uuid.uuid4().hex}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm="HS256")


def decode_access_token(token: str) -> dict | None:
    """解密JWT Token，验证签名和过期时间；失败返回None而非抛异常，简化调用方处理"""
    try:
        return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=["HS256"])
    except JWTError:
        return None
