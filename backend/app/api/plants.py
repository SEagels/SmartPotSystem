from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services import plant_service

router = APIRouter(prefix="/plants")


@router.get("")
async def list_plants(db: AsyncSession = Depends(get_db)):
    plants = await plant_service.get_all(db)
    return {"code": 0, "message": "success", "data": plants}


@router.get("/{plant_type}")
async def get_plant(plant_type: str, db: AsyncSession = Depends(get_db)):
    plant = await plant_service.get_by_type(db, plant_type)
    if not plant:
        return {"code": 3001, "message": "品种不存在", "data": None}
    return {"code": 0, "message": "success", "data": plant}
