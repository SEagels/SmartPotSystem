from __future__ import annotations

import asyncio
import json
import os

from app.config import settings
from app.core.database import get_engine, get_sessionmaker


async def seed_plant_types():
    from app.models.plant import PlantType
    seed_file = os.path.join(os.path.dirname(__file__), "plant_types.json")
    if not os.path.exists(seed_file):
        print("plant_types.json not found, skipping seed")
        return
    with open(seed_file, encoding="utf-8") as f:
        data = json.load(f)

    engine = get_engine()
    async with engine.begin() as conn:
        from sqlalchemy import select
        result = await conn.execute(select(PlantType.plant_type))
        existing = {r[0] for r in result}
        for item in data:
            if item["plant_type"] in existing:
                continue
            pt = PlantType(
                plant_type=item["plant_type"],
                name=item["name"],
                category=item["category"],
                default_thresholds=json.dumps(item["default_thresholds"], ensure_ascii=False),
                watering_cfg=json.dumps(item["watering_cfg"], ensure_ascii=False),
            )
            conn.add(pt)
            print(f"Inserted plant type: {item['name']}")
        await conn.commit()


if __name__ == "__main__":
    asyncio.run(seed_plant_types())
