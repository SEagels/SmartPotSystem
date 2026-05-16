from __future__ import annotations

import json

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.device import Device
from app.models.plant import PlantType
from app.services import command_service


def _watering_runtime_config(watering_cfg: dict) -> dict | None:
    trigger = watering_cfg.get("trigger_soil_moisture")
    duration = watering_cfg.get("default_duration_ms")
    if trigger is None:
        return None
    return {
        "auto_water_enabled": True,
        "auto_water_soil_moisture_min": float(trigger),
        "soil_moisture_threshold": float(trigger),
        "auto_water_duration_ms": int(duration or 5000),
        "default_duration_ms": int(duration or 5000),
    }


async def get_all(db: AsyncSession) -> list[dict]:
    result = await db.execute(select(PlantType).order_by(PlantType.name))
    plants = result.scalars().all()
    return [_plant_to_dict(p) for p in plants]


async def get_by_type(db: AsyncSession, plant_type: str) -> dict | None:
    result = await db.execute(select(PlantType).where(PlantType.plant_type == plant_type))
    p = result.scalar_one_or_none()
    if not p:
        return None
    return _plant_to_dict(p)


async def create_plant(db: AsyncSession, data: dict) -> dict:
    pt = PlantType(
        plant_type=data["plant_type"],
        name=data["name"],
        category=data["category"],
        default_thresholds=json.dumps(data["default_thresholds"], ensure_ascii=False),
        watering_cfg=json.dumps(data["watering_cfg"], ensure_ascii=False),
    )
    db.add(pt)
    await db.flush()
    return _plant_to_dict(pt)


async def update_plant(db: AsyncSession, plant_type: str, data: dict) -> dict | None:
    result = await db.execute(select(PlantType).where(PlantType.plant_type == plant_type))
    plant = result.scalar_one_or_none()
    if not plant:
        return None

    if "name" in data:
        plant.name = data["name"]
    if "category" in data:
        plant.category = data["category"]
    if "icon_url" in data:
        plant.icon_url = data["icon_url"]
    if "default_thresholds" in data:
        plant.default_thresholds = json.dumps(data["default_thresholds"], ensure_ascii=False)
    if "watering_cfg" in data:
        plant.watering_cfg = json.dumps(data["watering_cfg"], ensure_ascii=False)

    await db.flush()
    if "watering_cfg" in data:
        await _sync_assigned_devices(db, plant.plant_type, data["watering_cfg"])
    return _plant_to_dict(plant)


async def _sync_assigned_devices(db: AsyncSession, plant_type: str, watering_cfg: dict) -> None:
    config = _watering_runtime_config(watering_cfg)
    if not config:
        return

    result = await db.execute(select(Device).where(Device.plant_type == plant_type))
    devices = result.scalars().all()
    for device in devices:
        device.soil_moisture_threshold = config["soil_moisture_threshold"]
        device.watering_max_duration_ms = config["auto_water_duration_ms"]
        if device.online:
            await command_service.send_config_command(db, device.device_id, device.user_id, config)


async def delete_plant(db: AsyncSession, plant_type: str) -> bool:
    result = await db.execute(select(PlantType).where(PlantType.plant_type == plant_type))
    plant = result.scalar_one_or_none()
    if not plant:
        return False

    await db.execute(
        update(Device)
        .where(Device.plant_type == plant_type)
        .values(plant_type=None)
    )
    await db.delete(plant)
    await db.flush()
    return True


def _plant_to_dict(p: PlantType) -> dict:
    return {
        "plant_type": p.plant_type,
        "name": p.name,
        "category": p.category,
        "icon_url": p.icon_url,
        "default_thresholds": json.loads(p.default_thresholds),
        "watering_cfg": json.loads(p.watering_cfg),
    }
