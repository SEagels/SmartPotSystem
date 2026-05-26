# 异步数据库引擎与会话管理层
# 设计：懒初始化单例模式 —— 引擎和会话工厂在首次请求时才创建，避免导入即连接
# 数据流：get_db() → FastAPI Depends依赖注入 → 路由层获取异步会话 → 自动commit/rollback
from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

logger = logging.getLogger(__name__)

# 懒初始化单例：避免模块导入时就建立数据库连接
_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None

# MQTT handler 并发写入 SQLite 时的串行锁（SQLite 仅支持单写者）
db_write_lock = asyncio.Lock()


def _set_sqlite_pragma(dbapi_connection, connection_record):
    """每个SQLite连接建立时启用WAL模式+忙等超时，解决并发写入报database is locked"""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()


def get_engine() -> AsyncEngine:
    """获取异步数据库引擎（懒初始化，线程安全依赖GIL）"""
    global _engine
    if _engine is None:
        if settings.USE_SQLITE:
            _engine = create_async_engine(
                settings.DATABASE_URL, echo=False,
                connect_args={"check_same_thread": False},
            )
            event.listen(_engine.sync_engine, "connect", _set_sqlite_pragma)
            logger.info("SQLite configured: WAL mode + 5s busy timeout")
        else:
            _engine = create_async_engine(
                settings.DATABASE_URL, echo=False,
                pool_size=10, max_overflow=20,
            )
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    """获取异步会话工厂（单例，expire_on_commit=False避免提交后立即访问属性时触发二次查询）"""
    global _sessionmaker
    if _sessionmaker is None:
        _sessionmaker = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _sessionmaker


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI依赖注入用异步会话生成器
    生命周期：请求进入→获取session→业务处理→自动commit→遇到异常则rollback
    注意：通过 db_write_lock 串行化所有 DB 访问，避免 SQLite 写冲突"""
    async with db_write_lock:
        async with get_sessionmaker()() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise


async def get_db_readonly() -> AsyncGenerator[AsyncSession, None]:
    """只读会话生成器 — 不持有 db_write_lock。

    SQLite WAL 模式支持读写并发，读操作无需等待写锁。
    用于轮询类接口（如 sync-sensors）的认证依赖，避免长时间占用写锁
    导致 MQTT handler 无法写入遥测数据。
    """
    async with get_sessionmaker()() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    """应用启动时初始化数据库"""
    engine = get_engine()
    # SQLite模式：自动建表（生产环境使用Alembic迁移）
    if settings.USE_SQLITE:
        from app.models.base import Base
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            await _ensure_sqlite_schema(conn)

    # 开发环境：自动填充种子数据，失败不影响启动
    if settings.IS_DEV:
        try:
            from seed_data.seed import seed_plant_types
            await seed_plant_types()
        except Exception:
            pass
        try:
            from seed_data.seed_demo import seed_demo
            await seed_demo()
        except Exception:
            pass


async def _ensure_sqlite_schema(conn) -> None:
    """Small dev-mode schema patches for databases created before new columns existed."""
    result = await conn.execute(text("PRAGMA table_info(devices)"))
    columns = {row[1] for row in result.fetchall()}
    if "last_seen_at" not in columns:
        await conn.execute(text("ALTER TABLE devices ADD COLUMN last_seen_at DATETIME"))

    result = await conn.execute(text("PRAGMA table_info(images)"))
    image_columns = {row[1] for row in result.fetchall()}
    if "enhanced_url" not in image_columns:
        await conn.execute(text("ALTER TABLE images ADD COLUMN enhanced_url VARCHAR(512)"))
    if "detection_source" not in image_columns:
        await conn.execute(text("ALTER TABLE images ADD COLUMN detection_source VARCHAR(16)"))
