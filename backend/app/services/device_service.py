# 设备管理服务 —— CRUD + 绑定解绑 + 在线状态 + 今日聚合统计
# 数据流：API路由 → 此服务层 → SQLAlchemy ORM查询 → 封装为前端友好的dict返回
# 注意：此层不直接操作HTTP（不抛HTTPException），异常由路由层处理
from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.models.device import Device
from app.models.plant import PlantType
from app.models.telemetry import Telemetry


async def list_user_devices(db: AsyncSession, user_id: uuid.UUID) -> list[dict]:
    """获取用户的所有设备列表，附带最新遥测片段和活动告警标记"""
    result = await db.execute(
        select(Device).where(Device.user_id == user_id).order_by(Device.bound_at.desc())
    )
    devices = result.scalars().all()
    output = []
    for d in devices:
        # 关联查询植株类型中文名
        plant_name = None
        if d.plant_type:
            pr = await db.execute(select(PlantType).where(PlantType.plant_type == d.plant_type))
            p = pr.scalar_one_or_none()
            if p:
                plant_name = p.name
        latest_telemetry = await _get_latest_telemetry_snippet(db, d.device_id)
        # 检查是否有未读告警（用于前端显示红点提醒）
        has_alert = await db.execute(
            select(func.count(Alert.alert_id)).where(
                Alert.device_id == d.device_id, Alert.is_read == False
            )
        )
        output.append({
            "device_id": d.device_id,
            "name": d.name,
            "plant_type": d.plant_type,
            "plant_type_name": plant_name,
            "online": d.online,
            "latest_telemetry": latest_telemetry,
            "has_active_alert": (has_alert.scalar() or 0) > 0,
            "bound_at": d.bound_at.strftime("%Y-%m-%dT%H:%M:%SZ") if d.bound_at else None,
        })
    return output


async def _get_latest_telemetry_snippet(db: AsyncSession, device_id: str) -> dict | None:
    """获取最近一条遥测数据摘要（仅温湿度和土壤湿度，用于列表卡片展示）"""
    result = await db.execute(
        select(Telemetry)
        .where(Telemetry.device_id == device_id)
        .order_by(Telemetry.time.desc())
        .limit(1)
    )
    t = result.scalar_one_or_none()
    if not t:
        return None
    return {
        "temperature": t.temperature,
        "humidity": t.humidity,
        "soil_moisture": t.soil_moisture,
        "timestamp": t.time.strftime("%Y-%m-%dT%H:%M:%SZ") if t.time else None,
    }


async def get_device_detail(db: AsyncSession, device_id: str, user_id: uuid.UUID) -> dict:
    """获取设备详情：基本属性 + 所属植株 + 环境阈值 + 拍照计划 + 今日概况"""
    result = await db.execute(
        select(Device).where(Device.device_id == device_id, Device.user_id == user_id)
    )
    device = result.scalar_one_or_none()
    if not device:
        raise ValueError("设备不存在")
    plant_name = None
    if device.plant_type:
        pr = await db.execute(select(PlantType).where(PlantType.plant_type == device.plant_type))
        p = pr.scalar_one_or_none()
        if p:
            plant_name = p.name
    # 从PlantType读取该植株的默认环境阈值
    thresholds = None
    if device.plant_type:
        pr = await db.execute(select(PlantType).where(PlantType.plant_type == device.plant_type))
        p = pr.scalar_one_or_none()
        if p and p.default_thresholds:
            thresholds = json.loads(p.default_thresholds)
    # 拍照计划JSON解析，若无则使用默认值
    photo_schedule = json.loads(device.photo_schedule) if device.photo_schedule else ["08:00", "12:00", "16:00"]
    today_summary = await _get_today_summary(db, device_id)
    return {
        "device_id": device.device_id,
        "name": device.name,
        "plant_type": device.plant_type,
        "plant_type_name": plant_name,
        "online": device.online,
        "firmware_version": device.firmware_version,
        "latest_telemetry": await _get_latest_telemetry_snippet(db, device_id),
        "thresholds": thresholds,
        "photo_schedule": photo_schedule,
        "today_summary": today_summary,
    }


async def _get_today_summary(db: AsyncSession, device_id: str) -> dict:
    """聚合今日数据：浇水次数/量 + 拍照次数 + 病害告警数"""
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    from app.models.image import Image
    from app.models.watering import WateringEvent
    w_result = await db.execute(
        select(func.count(WateringEvent.event_id), func.coalesce(func.sum(WateringEvent.water_pumped_ml), 0))
        .where(WateringEvent.device_id == device_id)
        .where(func.date(WateringEvent.timestamp) == today)
    )
    w_count, w_ml = w_result.one()
    p_result = await db.execute(
        select(func.count(Image.image_id))
        .where(Image.device_id == device_id)
        .where(func.date(Image.timestamp) == today)
    )
    p_count = p_result.scalar() or 0
    a_result = await db.execute(
        select(func.count(Alert.alert_id))
        .where(Alert.device_id == device_id, Alert.type == "disease_detected")
        .where(func.date(Alert.created_at) == today)
    )
    a_count = a_result.scalar() or 0
    return {"watering_count": w_count, "watering_total_ml": float(w_ml), "photo_count": p_count, "disease_alerts": a_count}


async def bind_device(db: AsyncSession, user_id: uuid.UUID, device_id: str, bind_code: str) -> Device:
    """设备绑定：验证设备存在、未被占用、绑定码匹配后关联到用户"""
    result = await db.execute(select(Device).where(Device.device_id == device_id))
    device = result.scalar_one_or_none()
    if not device:
        raise ValueError("设备不存在")
    if device.user_id:
        raise ValueError("设备已被其他用户绑定")
    if device.bind_code != bind_code:
        raise ValueError("绑定码错误")
    device.user_id = user_id
    device.bound_at = datetime.now(UTC)
    device.name = f"新设备-{device_id}"  # 绑定后自动生成默认名称
    return device


async def update_device(db: AsyncSession, device_id: str, user_id: uuid.UUID, data: dict) -> Device:
    """更新设备设置：名称、关联植株类型"""
    result = await db.execute(
        select(Device).where(Device.device_id == device_id, Device.user_id == user_id)
    )
    device = result.scalar_one_or_none()
    if not device:
        raise ValueError("设备不存在")
    if "name" in data and data["name"]:
        device.name = data["name"]
    if "plant_type" in data and data["plant_type"]:
        device.plant_type = data["plant_type"]
    return device


async def unbind_device(db: AsyncSession, device_id: str, user_id: uuid.UUID) -> None:
    """解除设备绑定：清空用户关联和植株类型（保留设备记录供重新绑定）"""
    result = await db.execute(
        select(Device).where(Device.device_id == device_id, Device.user_id == user_id)
    )
    device = result.scalar_one_or_none()
    if not device:
        raise ValueError("设备不存在")
    device.user_id = None
    device.plant_type = None
    device.bound_at = None


async def update_online_status(db: AsyncSession, device_id: str, online: bool, status_data: dict | None = None) -> None:
    """MQTT设备状态回调：更新在线标识和固件版本"""
    result = await db.execute(select(Device).where(Device.device_id == device_id))
    device = result.scalar_one_or_none()
    if device:
        device.online = online
        if status_data:
            if status_data.get("firmware_version"):
                device.firmware_version = status_data["firmware_version"]
