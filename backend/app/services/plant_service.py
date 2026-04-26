from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plant import PlantType


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


def _plant_to_dict(p: PlantType) -> dict:
    return {
        "plant_type": p.plant_type,
        "name": p.name,
        "category": p.category,
        "icon_url": p.icon_url,
        "default_thresholds": json.loads(p.default_thresholds),
        "watering_cfg": json.loads(p.watering_cfg),
    }
