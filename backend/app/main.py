# SmartPot 应用入口 —— FastAPI 应用工厂 + 生命周期管理
# 启动顺序: 数据库初始化 → 后台Worker启动 → API就绪
# 关闭顺序: Worker停止 → WebSocket断开 → Redis释放
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.router import router
from app.config import settings
from app.core.database import init_db
from app.core.redis import close_redis
from app.core.websocket_manager import ws_manager

logger = logging.getLogger(__name__)

# 报告生成器任务句柄，仅生产环境启用
_report_task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI生命周期管理：控制所有长生命周期资源（DB/MQTT/Worker）的初始化与优雅关闭"""
    global _report_task

    # 启动阶段：先建表 → 启动本地MQTT Broker → 拉起后台Worker
    await init_db()

    # 开发模式下启动本地内嵌MQTT Broker（无需外部EMQX/Mosquitto）
    if settings.IS_DEV:
        from app.core.local_broker import start_local_broker
        await start_local_broker(host="0.0.0.0", port=settings.MQTT_BROKER_PORT)

    # 遥测消费者和图像处理Worker各自独立运行，任一失败不影响启动
    _telemetry_task = asyncio.create_task(_safe_start_telemetry())
    _image_task = asyncio.create_task(_safe_start_image_processor())

    # 自动补水检查（基于植物推荐湿度阈值，每60秒轮询）
    _auto_water_task = asyncio.create_task(_safe_start_auto_watering())
    # 定时拍照调度（按设备photo_schedule触发，每30秒检查）
    _photo_schedule_task = asyncio.create_task(_safe_start_photo_scheduler())

    # 定时养护报告生成器仅在正式环境运行（避免开发时频繁生成）
    if settings.IS_PROD:
        from app.worker.report_generator import start_report_generator, stop_report_generator
        _report_task = asyncio.create_task(start_report_generator())

    yield  # ← 应用在此处正式对外服务

    # 关闭阶段：按依赖顺序反向清理（先停数据生产者，再断开连接，最后释放资源）
    from app.worker.auto_watering import stop_auto_watering
    from app.worker.image_processor import stop_image_processor
    from app.worker.photo_scheduler import stop_photo_scheduler
    from app.worker.telemetry_consumer import stop_telemetry_consumer
    await stop_auto_watering()
    await stop_photo_scheduler()
    await stop_telemetry_consumer()
    await stop_image_processor()

    if _report_task:
        from app.worker.report_generator import stop_report_generator
        await stop_report_generator()
        _report_task.cancel()
        try:
            await _report_task
        except asyncio.CancelledError:
            pass  # 预期内的取消异常，无需处理

    await ws_manager.close_all()
    await close_redis()

    # 关闭本地MQTT Broker
    if settings.IS_DEV:
        from app.core.local_broker import stop_local_broker
        await stop_local_broker()


async def _safe_start_telemetry():
    """安全启动遥测消费者：Worker启动失败不应导致整个应用崩溃"""
    from app.worker.telemetry_consumer import start_telemetry_consumer
    try:
        await start_telemetry_consumer()
    except Exception:
        logger.exception("Failed to start MQTT telemetry consumer")


async def _safe_start_image_processor():
    """安全启动图像处理器：同理，隔离启动失败对应用的影响"""
    from app.worker.image_processor import start_image_processor
    try:
        await start_image_processor()
    except Exception:
        logger.exception("Failed to start image processor")


async def _safe_start_auto_watering():
    """安全启动自动补水检查器"""
    from app.worker.auto_watering import start_auto_watering
    try:
        await start_auto_watering()
    except Exception:
        logger.exception("Failed to start auto-watering worker")


async def _safe_start_photo_scheduler():
    """安全启动定时拍照调度器"""
    from app.worker.photo_scheduler import start_photo_scheduler
    try:
        await start_photo_scheduler()
    except Exception:
        logger.exception("Failed to start photo scheduler")


app = FastAPI(
    title="SmartPot API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS全开：移动端/Web/物联网设备混合访问场景下，暂时不限制来源
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 所有业务路由统一注册在 /v1 前缀下
app.include_router(router)

# 挂载静态文件目录（病害图片等）
_static_dir = Path(__file__).resolve().parent.parent / "storage" / "images"
_static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static/images", StaticFiles(directory=str(_static_dir)), name="static_images")


@app.get("/health")
async def health():
    """健康检查端点：供负载均衡或监控探活使用"""
    return {"status": "ok", "environment": settings.ENVIRONMENT}
