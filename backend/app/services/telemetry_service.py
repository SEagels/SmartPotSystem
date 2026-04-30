from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.telemetry import Telemetry


async def ingest_telemetry(db: AsyncSession, device_id: str, data: dict) -> Telemetry:
    sensors = data.get("sensors", {})
    actuators = data.get("actuators", {})
    system = data.get("system", {})

    t = Telemetry(
        time=datetime.now(UTC),
        device_id=device_id,
        sequence=data.get("sequence"),
        temperature=sensors.get("temperature"),
        humidity=sensors.get("humidity"),
        soil_moisture=sensors.get("soil_moisture"),
        light_intensity=sensors.get("light_intensity"),
        pump_running=actuators.get("pump_running", False),
        led_on=actuators.get("led_on", False),
        wifi_rssi=system.get("wifi_rssi"),
        free_heap_kb=system.get("free_heap_kb"),
        uptime_s=system.get("uptime_s"),
        firmware_version=system.get("firmware_version"),
    )
    db.add(t)
    await db.flush()
    return t


async def get_latest_telemetry(db: AsyncSession, device_id: str) -> dict | None:
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
        "device_id": t.device_id,
        "timestamp": t.time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sensors": {
            "temperature": t.temperature,
            "humidity": t.humidity,
            "soil_moisture": t.soil_moisture,
            "light_intensity": t.light_intensity,
        },
        "actuators": {
            "pump_running": t.pump_running,
            "led_on": t.led_on,
        },
        "system": {
            "wifi_rssi": t.wifi_rssi,
            "free_heap_kb": t.free_heap_kb,
            "uptime_s": t.uptime_s,
            "firmware_version": t.firmware_version,
        },
    }


async def get_history(
    db: AsyncSession,
    device_id: str,
    metric: str,
    start: datetime,
    end: datetime,
    interval: str = "1h",
) -> dict:
    metric_col = getattr(Telemetry, metric, None)
    if metric_col is None:
        raise ValueError(f"不支持的指标: {metric}")

    if settings.USE_SQLITE:
        return await _get_history_sqlite(db, device_id, metric, start, end, interval)
    return await _get_history_timescale(db, device_id, metric, start, end, interval)


async def _get_history_timescale(
    db, device_id: str, metric: str, start: datetime, end: datetime, interval: str
) -> dict:
    bucket_map = {"5m": "5 minutes", "1h": "1 hour", "6h": "6 hours", "1d": "1 day"}
    bucket = bucket_map.get(interval, "1 hour")
    sql = text(f"""
        SELECT time_bucket(:bucket, time) AS bucket,
               AVG({metric}) AS avg_val,
               MIN({metric}) AS min_val,
               MAX({metric}) AS max_val
        FROM telemetry
        WHERE device_id = :device_id AND time BETWEEN :start AND :end
        GROUP BY bucket ORDER BY bucket
    """)
    result = await db.execute(sql, {"bucket": bucket, "device_id": device_id, "start": start, "end": end})
    data_points = [
        {"timestamp": row.bucket.strftime("%Y-%m-%dT%H:%M:%SZ"), "avg": round(row.avg_val, 2),
         "min": round(row.min_val, 2), "max": round(row.max_val, 2)}
        for row in result
    ]
    unit_map = {"temperature": "°C", "humidity": "%", "soil_moisture": "%", "light_intensity": "lux"}
    return {"metric": metric, "unit": unit_map.get(metric, ""), "interval": interval, "data_points": data_points}


async def _get_history_sqlite(
    db, device_id: str, metric: str, start: datetime, end: datetime, interval: str
) -> dict:
    result = await db.execute(
        select(Telemetry)
        .where(Telemetry.device_id == device_id, Telemetry.time.between(start, end))
        .order_by(Telemetry.time.asc())
    )
    rows = result.scalars().all()
    if not rows:
        return {"metric": metric, "unit": "", "interval": interval, "data_points": []}

    buckets: dict[str, list[float]] = {}
    minutes_map = {"5m": 5, "1h": 60, "6h": 360, "1d": 1440}
    bucket_minutes = minutes_map.get(interval, 60)

    for row in rows:
        ts = row.time
        if bucket_minutes >= 1440:
            key = ts.strftime("%Y-%m-%d")
        else:
            minute_block = (ts.minute // bucket_minutes) * bucket_minutes
            key = ts.replace(minute=minute_block, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")
        val = getattr(row, metric, None)
        if val is not None:
            buckets.setdefault(key, []).append(val)

    data_points = [
        {"timestamp": k, "avg": round(sum(v) / len(v), 2),
         "min": round(min(v), 2), "max": round(max(v), 2)}
        for k, v in sorted(buckets.items())
    ]
    unit_map = {"temperature": "°C", "humidity": "%", "soil_moisture": "%", "light_intensity": "lux"}
    return {"metric": metric, "unit": unit_map.get(metric, ""), "interval": interval, "data_points": data_points}


async def get_daily_summary(db: AsyncSession, device_id: str, date_str: str) -> dict:
    day_start = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=UTC)
    day_end = day_start + timedelta(days=1)

    result = await db.execute(
        select(Telemetry)
        .where(Telemetry.device_id == device_id, Telemetry.time.between(day_start, day_end))
        .order_by(Telemetry.time.asc())
    )
    rows = result.scalars().all()

    def _stats(attr):
        vals = [getattr(r, attr) for r in rows if getattr(r, attr) is not None]
        if not vals:
            return {"avg": None, "min": None, "max": None}
        return {"avg": round(sum(vals) / len(vals), 2), "min": round(min(vals), 2), "max": round(max(vals), 2)}

    return {
        "device_id": device_id,
        "date": date_str,
        "data_point_count": len(rows),
        "temperature": _stats("temperature"),
        "humidity": _stats("humidity"),
        "soil_moisture": _stats("soil_moisture"),
        "light_intensity": _stats("light_intensity"),
    }
