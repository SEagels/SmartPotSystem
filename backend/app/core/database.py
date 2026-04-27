# 异步数据库引擎与会话管理层
# 设计：懒初始化单例模式 —— 引擎和会话工厂在首次请求时才创建，避免导入即连接
# 数据流：get_db() → FastAPI Depends依赖注入 → 路由层获取异步会话 → 自动commit/rollback
from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

# 懒初始化单例：避免模块导入时就建立数据库连接
_engine: AsyncEngine | None = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """获取异步数据库引擎（懒初始化，线程安全依赖GIL）"""
    global _engine
    if _engine is None:
        if settings.USE_SQLITE:
            # SQLite限制：异步下必须禁用同线程检查
            _engine = create_async_engine(
                settings.DATABASE_URL, echo=False,
                connect_args={"check_same_thread": False},
            )
        else:
            # PostgreSQL/TimescaleDB：配置连接池
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
    生命周期：请求进入→获取session→业务处理→自动commit→遇到异常则rollback"""
    async with get_sessionmaker()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """应用启动时初始化数据库"""
    engine = get_engine()
    # SQLite模式：自动建表（生产环境使用Alembic迁移）
    if settings.USE_SQLITE:
        from app.models.base import Base
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

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
