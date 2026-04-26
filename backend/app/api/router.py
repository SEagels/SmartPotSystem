from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.devices import router as devices_router
from app.api.telemetry import router as telemetry_router
from app.api.images import router as images_router
from app.api.diseases import router as diseases_router
from app.api.alerts import router as alerts_router
from app.api.control import router as control_router
from app.api.reports import router as reports_router
from app.api.plants import router as plants_router
from app.api.ws import router as ws_router

router = APIRouter(prefix="/v1")
router.include_router(auth_router, tags=["认证"])
router.include_router(devices_router, tags=["设备管理"])
router.include_router(telemetry_router, tags=["遥测数据"])
router.include_router(images_router, tags=["图片与检测"])
router.include_router(diseases_router, tags=["病害记录"])
router.include_router(alerts_router, tags=["告警"])
router.include_router(control_router, tags=["远程控制"])
router.include_router(reports_router, tags=["养护报告"])
router.include_router(plants_router, tags=["植物品种"])
router.include_router(ws_router, tags=["实时推送"])
