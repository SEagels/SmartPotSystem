from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
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


@router.post("", status_code=201)
async def create_plant(data: dict, db: AsyncSession = Depends(get_db)):
    existing = await plant_service.get_by_type(db, data.get("plant_type", ""))
    if existing:
        raise HTTPException(status_code=409, detail="品种代码已存在")
    plant = await plant_service.create_plant(db, data)
    return {"code": 0, "message": "创建成功", "data": plant}


@router.put("/{plant_type}")
async def update_plant(plant_type: str, data: dict, db: AsyncSession = Depends(get_db)):
    data.pop("plant_type", None)
    plant = await plant_service.update_plant(db, plant_type, data)
    if not plant:
        return {"code": 3001, "message": "品种不存在", "data": None}
    return {"code": 0, "message": "更新成功", "data": plant}


@router.delete("/{plant_type}")
async def delete_plant(plant_type: str, db: AsyncSession = Depends(get_db)):
    deleted = await plant_service.delete_plant(db, plant_type)
    if not deleted:
        return {"code": 3001, "message": "品种不存在", "data": None}
    return {"code": 0, "message": "删除成功", "data": None}
