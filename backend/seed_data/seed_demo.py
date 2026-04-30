"""
Rich demo data seeder — covers multiple users, devices, telemetry patterns,
disease detections, alerts of all types, watering events, and commands.

Usage:  cd backend && python -m seed_data.seed_demo
"""
from __future__ import annotations

import asyncio
import json
import random
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, func
from app.core.database import get_engine, get_sessionmaker
from app.core.security import hash_password

NOW = datetime.now(UTC).replace(second=0, microsecond=0)
HOUR = timedelta(hours=1)
DAY = timedelta(days=1)
MIN5 = timedelta(minutes=5)

USER_1_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
USER_2_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")


def ts_dt(offset: timedelta) -> datetime:
    return NOW + offset


def rand_float(mean: float, dev: float) -> float:
    return round(random.gauss(mean, dev), 1)


async def seed_demo():
    # Ensure tables exist (idempotent)
    engine = get_engine()
    from app.models.base import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    sm = get_sessionmaker()
    async with sm() as session:
        await _seed_users(session)
        await _seed_devices(session)
        await _seed_telemetry(session)
        await _seed_images(session)
        await _seed_watering(session)
        await _seed_commands(session)
        await _seed_alerts(session)
        await session.commit()

    print("Demo data seeded successfully!")
    print("  Users:    2  (demo_user / test_gardener, 密码均为 123456)")
    print("  Devices:  4")
    print("  Telemetry records: ~2000")
    print("  Images:   6")
    print("  Detections: 3")
    print("  Alerts:   6")
    print("  Watering: 9")
    print("  Commands: 5")


# ───────────────── Users ─────────────────

async def _seed_users(session):
    from app.models.user import User

    r = await session.execute(select(User).where(User.id == USER_1_ID))
    if r.scalar_one_or_none():
        return

    session.add_all([
        User(id=USER_1_ID, username="demo_user", password_hash=hash_password("123456"),
             phone="13800001111", created_at=ts_dt(-DAY * 30)),
        User(id=USER_2_ID, username="test_gardener", password_hash=hash_password("123456"),
             phone="13900002222", created_at=ts_dt(-DAY * 14)),
    ])
    print("  -> 2 users inserted")


# ───────────────── Devices ─────────────────

async def _seed_devices(session):
    from app.models.device import Device

    r = await session.execute(select(Device).where(Device.device_id == "SP000001"))
    if r.scalar_one_or_none():
        return

    session.add_all([
        Device(device_id="SP000001", user_id=USER_1_ID, name="客厅龟背竹",
               plant_type="monstera_deliciosa", bind_code="A1B2C3D4",
               online=True, firmware_version="v1.2.3",
               photo_schedule='["08:00","12:00","16:00"]',
               soil_moisture_threshold=25.0, watering_max_duration_ms=30000,
               bound_at=ts_dt(-DAY * 28)),
        Device(device_id="SP000002", user_id=USER_1_ID, name="阳台绿萝",
               plant_type="epipremnum_aureum", bind_code="B2C3D4E5",
               online=False, firmware_version="v1.2.3",
               photo_schedule='["08:00","12:00","16:00"]',
               soil_moisture_threshold=30.0, watering_max_duration_ms=20000,
               bound_at=ts_dt(-DAY * 21)),
        Device(device_id="SP000003", user_id=USER_1_ID, name="书房蝴蝶兰",
               plant_type="phalaenopsis", bind_code="C3D4E5F6",
               online=False, firmware_version="v1.1.0",
               photo_schedule='["09:00","15:00"]',
               soil_moisture_threshold=35.0, watering_max_duration_ms=30000,
               bound_at=ts_dt(-DAY * 14)),
        Device(device_id="SP000004", user_id=USER_2_ID, name="卧室芦荟",
               plant_type="aloe_vera", bind_code="D4E5F6A7",
               online=True, firmware_version="v1.2.3",
               photo_schedule='["08:00","18:00"]',
               soil_moisture_threshold=20.0, watering_max_duration_ms=15000,
               bound_at=ts_dt(-DAY * 2)),
    ])
    print("  -> 4 devices inserted")


# ───────────────── Telemetry ─────────────────

async def _seed_telemetry(session):
    from app.models.telemetry import Telemetry

    r = await session.execute(select(func.count()).select_from(Telemetry))
    if r.scalar() > 0:
        return

    patterns = {
        "SP000001": (25.0, 1.5, 62.0, 5.0, 42.0, 3.0, 800),
        "SP000002": (27.0, 2.0, 55.0, 8.0, 35.0, 4.0, 1200),
        "SP000003": (23.0, 1.0, 70.0, 4.0, 48.0, 2.0, 500),
        "SP000004": (26.0, 1.2, 50.0, 6.0, 55.0, 2.5, 700),
    }

    batch = []
    total = 0

    for device_id, (tm, td, hm, hd, sm, sd, lb) in patterns.items():
        seq = 0
        end_offset = -DAY if device_id == "SP000003" else (-timedelta(hours=2) if device_id == "SP000002" else timedelta(0))
        start_offset = -DAY if device_id == "SP000004" else -DAY * 3

        t = NOW + start_offset
        end = NOW + end_offset

        while t < end:
            hour = t.hour
            if 6 <= hour < 18:
                temp = rand_float(tm + 1, td)
                light = rand_float(lb, lb * 0.3)
            else:
                temp = rand_float(tm - 1, td)
                light = 0

            hum = rand_float(hm, hd)
            soil = max(15.0, min(65.0, rand_float(sm, sd)))
            tank = max(5.0, min(100.0, rand_float(60.0, 15.0)))

            if random.random() < 0.03:
                soil = max(35.0, soil + random.uniform(10, 20))

            batch.append(Telemetry(
                time=t, device_id=device_id, sequence=seq,
                temperature=round(temp, 1), humidity=round(hum, 1),
                soil_moisture=round(min(65.0, max(15.0, soil)), 1),
                light_intensity=round(light, 1),
                pump_running=False, led_on=(hour < 6 or hour >= 18),
                wifi_rssi=random.randint(-60, -30),
                free_heap_kb=random.randint(200, 300),
                uptime_s=int((t - (NOW + start_offset)).total_seconds()),
                firmware_version="v1.2.3",
            ))
            seq += 1
            t += MIN5

            # Flush every 500 rows
            if len(batch) >= 500:
                session.add_all(batch)
                await session.flush()
                total += len(batch)
                batch = []

    if batch:
        session.add_all(batch)
        total += len(batch)

    print(f"  -> {total} telemetry records inserted")


# ───────────────── Images + Detections ─────────────────

async def _seed_images(session):
    from app.models.image import Image
    from app.models.detection import Detection

    r = await session.execute(select(Image).where(Image.device_id == "SP000001"))
    if r.scalar_one_or_none():
        return

    session.add_all([
        Image(image_id="IMG-DEMO-001", device_id="SP000001", user_id=USER_1_ID,
              timestamp=ts_dt(-HOUR * 6), photo_index=1, burst_total=3,
              quality_score=0.92, light_condition="natural", resolution="1600x1200",
              file_size_bytes=245760, format="jpg",
              url="https://picsum.photos/seed/plant1/800/600",
              detection_status="completed", health_score=65, disease_count=2),
        Image(image_id="IMG-DEMO-002", device_id="SP000001", user_id=USER_1_ID,
              timestamp=ts_dt(-HOUR * 3), photo_index=1, burst_total=3,
              quality_score=0.88, light_condition="led_fill", resolution="1600x1200",
              file_size_bytes=230400, format="jpg",
              url="https://picsum.photos/seed/plant2/800/600",
              detection_status="completed", health_score=78, disease_count=1),
        Image(image_id="IMG-DEMO-003", device_id="SP000001", user_id=USER_1_ID,
              timestamp=ts_dt(-HOUR * 1), photo_index=2, burst_total=3,
              quality_score=0.95, light_condition="natural", resolution="1600x1200",
              file_size_bytes=251200, format="jpg",
              url="https://picsum.photos/seed/plant3/800/600",
              detection_status="completed", health_score=92, disease_count=0),
        Image(image_id="IMG-DEMO-004", device_id="SP000002", user_id=USER_1_ID,
              timestamp=ts_dt(-HOUR * 5), photo_index=1, burst_total=3,
              quality_score=0.90, light_condition="natural", resolution="1600x1200",
              file_size_bytes=240000, format="jpg",
              url="https://picsum.photos/seed/plant4/800/600",
              detection_status="completed", health_score=95, disease_count=0),
        Image(image_id="IMG-DEMO-005", device_id="SP000002", user_id=USER_1_ID,
              timestamp=ts_dt(-HOUR * 2), photo_index=1, burst_total=3,
              quality_score=0.85, light_condition="led_fill", resolution="1600x1200",
              file_size_bytes=235000, format="jpg",
              url="https://picsum.photos/seed/plant5/800/600",
              detection_status="completed", health_score=90, disease_count=0),
        Image(image_id="IMG-DEMO-006", device_id="SP000004", user_id=USER_2_ID,
              timestamp=ts_dt(-HOUR * 1), photo_index=1, burst_total=3,
              quality_score=0.78, light_condition="low_light", resolution="1600x1200",
              file_size_bytes=180000, format="jpg",
              url="https://picsum.photos/seed/plant6/800/600",
              detection_status="pending_detection", health_score=None, disease_count=0),
    ])

    session.add_all([
        Detection(detection_id="DET-0001", image_id="IMG-DEMO-001", device_id="SP000001",
                  timestamp=ts_dt(-HOUR * 6 + MIN5),
                  disease_class="Leaf Spot", disease_name="叶斑病",
                  confidence=0.87, severity="moderate",
                  bbox=json.dumps({"x": 120, "y": 85, "width": 200, "height": 180}),
                  recommendation="建议喷洒多菌灵800倍液，间隔7天重复一次", health_score=65),
        Detection(detection_id="DET-0002", image_id="IMG-DEMO-001", device_id="SP000001",
                  timestamp=ts_dt(-HOUR * 6 + MIN5),
                  disease_class="Powdery Mildew Leaf", disease_name="白粉病叶",
                  confidence=0.72, severity="mild",
                  bbox=json.dumps({"x": 350, "y": 200, "width": 150, "height": 120}),
                  recommendation="加强通风，喷洒硫磺制剂", health_score=65),
        Detection(detection_id="DET-0003", image_id="IMG-DEMO-002", device_id="SP000001",
                  timestamp=ts_dt(-HOUR * 3 + MIN5),
                  disease_class="Gray Mold", disease_name="灰霉病",
                  confidence=0.91, severity="moderate",
                  bbox=json.dumps({"x": 200, "y": 100, "width": 180, "height": 160}),
                  recommendation="降低环境湿度，喷洒腐霉利1000倍液", health_score=78),
    ])
    print("  -> 6 images + 3 detections inserted")


# ───────────────── Watering Events ─────────────────

async def _seed_watering(session):
    from app.models.watering import WateringEvent

    r = await session.execute(select(WateringEvent).where(WateringEvent.device_id == "SP000001"))
    if r.scalar_one_or_none():
        return

    session.add_all([
        WateringEvent(event_id="EVT-W-0001", device_id="SP000001", timestamp=ts_dt(-DAY * 2 + HOUR * 8),
                      trigger="auto", duration_ms=8000, water_pumped_ml=80,
                      reason="soil_moisture_below_threshold", soil_moisture_before=23.5, soil_moisture_after=48.2),
        WateringEvent(event_id="EVT-W-0002", device_id="SP000001", timestamp=ts_dt(-DAY * 1 + HOUR * 8),
                      trigger="auto", duration_ms=8000, water_pumped_ml=78,
                      reason="soil_moisture_below_threshold", soil_moisture_before=22.0, soil_moisture_after=46.5),
        WateringEvent(event_id="EVT-W-0003", device_id="SP000001", timestamp=ts_dt(-DAY * 1 + HOUR * 14),
                      trigger="manual", duration_ms=5000, water_pumped_ml=50,
                      reason="manual_override", soil_moisture_before=28.0, soil_moisture_after=42.0),
        WateringEvent(event_id="EVT-W-0004", device_id="SP000001", timestamp=ts_dt(-HOUR * 8),
                      trigger="auto", duration_ms=8000, water_pumped_ml=82,
                      reason="soil_moisture_below_threshold", soil_moisture_before=24.1, soil_moisture_after=47.8),
        WateringEvent(event_id="EVT-W-0005", device_id="SP000002", timestamp=ts_dt(-DAY * 2 + HOUR * 9),
                      trigger="auto", duration_ms=6000, water_pumped_ml=60,
                      reason="soil_moisture_below_threshold", soil_moisture_before=28.0, soil_moisture_after=52.0),
        WateringEvent(event_id="EVT-W-0006", device_id="SP000002", timestamp=ts_dt(-DAY * 1 + HOUR * 9),
                      trigger="auto", duration_ms=6000, water_pumped_ml=58,
                      reason="soil_moisture_below_threshold", soil_moisture_before=29.0, soil_moisture_after=51.0),
        WateringEvent(event_id="EVT-W-0007", device_id="SP000003", timestamp=ts_dt(-DAY * 2 + HOUR * 8),
                      trigger="auto", duration_ms=10000, water_pumped_ml=100,
                      reason="soil_moisture_below_threshold", soil_moisture_before=33.0, soil_moisture_after=55.0),
        WateringEvent(event_id="EVT-W-0008", device_id="SP000003", timestamp=ts_dt(-DAY * 1 + HOUR * 8),
                      trigger="auto", duration_ms=10000, water_pumped_ml=0,
                      reason="soil_moisture_below_threshold", soil_moisture_before=32.5, soil_moisture_after=32.5),
        WateringEvent(event_id="EVT-W-0009", device_id="SP000004", timestamp=ts_dt(-HOUR * 12),
                      trigger="manual", duration_ms=4000, water_pumped_ml=40,
                      reason="manual_override", soil_moisture_before=18.5, soil_moisture_after=38.0),
    ])
    print("  -> 9 watering events inserted")


# ───────────────── Commands ─────────────────

async def _seed_commands(session):
    from app.models.command import Command

    r = await session.execute(select(Command).where(Command.device_id == "SP000001"))
    if r.scalar_one_or_none():
        return

    session.add_all([
        Command(cmd_id="CMD-W-0001", device_id="SP000001", user_id=USER_1_ID,
                type="water", status="executed",
                request=json.dumps({"duration_ms": 5000, "source": "manual"}),
                response=json.dumps({"actual_duration_ms": 5000, "water_pumped_ml": 50}),
                created_at=ts_dt(-DAY * 1 + HOUR * 14),
                completed_at=ts_dt(-DAY * 1 + HOUR * 14 + timedelta(seconds=6))),
        Command(cmd_id="CMD-P-0001", device_id="SP000001", user_id=USER_1_ID,
                type="photo", status="executed",
                request=json.dumps({"burst_count": 3, "source": "manual"}),
                response=json.dumps({"image_count": 3, "selected_index": 1}),
                created_at=ts_dt(-HOUR * 6 + timedelta(minutes=5)),
                completed_at=ts_dt(-HOUR * 6 + timedelta(seconds=4))),
        Command(cmd_id="CMD-W-0002", device_id="SP000003", user_id=USER_1_ID,
                type="water", status="failed",
                request=json.dumps({"duration_ms": 5000, "source": "manual"}),
                response=None,
                created_at=ts_dt(-DAY * 1 + HOUR * 2),
                completed_at=ts_dt(-DAY * 1 + HOUR * 2 + timedelta(seconds=30))),
        Command(cmd_id="CMD-W-0003", device_id="SP000004", user_id=USER_2_ID,
                type="water", status="executed",
                request=json.dumps({"duration_ms": 4000, "source": "manual"}),
                response=json.dumps({"actual_duration_ms": 4000, "water_pumped_ml": 40}),
                created_at=ts_dt(-HOUR * 12),
                completed_at=ts_dt(-HOUR * 12 + timedelta(seconds=5))),
        Command(cmd_id="CMD-C-0001", device_id="SP000001", user_id=USER_1_ID,
                type="config", status="applied",
                request=json.dumps({"photo_schedule": ["07:00", "12:00", "18:00"]}),
                response=json.dumps({"status": "applied"}),
                created_at=ts_dt(-DAY * 2 + HOUR * 10),
                completed_at=ts_dt(-DAY * 2 + HOUR * 10 + timedelta(seconds=2))),
    ])
    print("  -> 5 commands inserted")


# ───────────────── Alerts ─────────────────

async def _seed_alerts(session):
    from app.models.alert import Alert

    r = await session.execute(select(Alert).where(Alert.device_id == "SP000001"))
    if r.scalar_one_or_none():
        return

    session.add_all([
        Alert(alert_id="ALT-0001", device_id="SP000001", user_id=USER_1_ID,
              type="disease_detected", severity="warning",
              title="检测到叶斑病",
              message="您的龟背竹(客厅)在叶片图像中检测到叶斑病，置信度87%。建议喷洒多菌灵800倍液。",
              image_id="IMG-DEMO-001", is_read=False, created_at=ts_dt(-HOUR * 6)),
        Alert(alert_id="ALT-0002", device_id="SP000001", user_id=USER_1_ID,
              type="disease_detected", severity="info",
              title="检测到白粉病叶",
              message="您的龟背竹(客厅)在叶片图像中检测到白粉病叶，置信度72%。建议加强通风。",
              image_id="IMG-DEMO-001", is_read=False, created_at=ts_dt(-HOUR * 6)),
        Alert(alert_id="ALT-0003", device_id="SP000001", user_id=USER_1_ID,
              type="disease_detected", severity="warning",
              title="检测到灰霉病",
              message="您的龟背竹(客厅)在叶片图像中检测到灰霉病，置信度91%。建议降低环境湿度。",
              image_id="IMG-DEMO-002", is_read=True, created_at=ts_dt(-HOUR * 3)),
        Alert(alert_id="ALT-0004", device_id="SP000003", user_id=USER_1_ID,
              type="water_low", severity="info",
              title="水箱余量不足",
              message="您的蝴蝶兰(书房)当前水箱余量仅12%，请及时加水。",
              image_id=None, is_read=False, created_at=ts_dt(-DAY * 1)),
        Alert(alert_id="ALT-0005", device_id="SP000003", user_id=USER_1_ID,
              type="device_offline", severity="critical",
              title="设备离线",
              message="您的蝴蝶兰(书房)已离线超过24小时，请检查设备供电和WiFi连接。",
              image_id=None, is_read=False, created_at=ts_dt(-DAY * 1)),
        Alert(alert_id="ALT-0006", device_id="SP000003", user_id=USER_1_ID,
              type="watering_failed", severity="warning",
              title="补水失败",
              message="您的蝴蝶兰(书房)自动补水指令执行失败，水泵可能干烧或无响应。",
              image_id=None, is_read=False, created_at=ts_dt(-DAY * 1 + HOUR * 2)),
    ])
    print("  -> 6 alerts inserted")


if __name__ == "__main__":
    asyncio.run(seed_demo())
