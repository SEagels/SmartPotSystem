from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.models.image import Image
from app.models.telemetry import Telemetry
from app.models.watering import WateringEvent


async def generate_daily_report(db: AsyncSession, device_id: str, date_str: str) -> dict:
    day_start = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=UTC)
    day_end = day_start + timedelta(days=1)

    t_result = await db.execute(
        select(Telemetry).where(Telemetry.device_id == device_id, Telemetry.time.between(day_start, day_end))
    )
    telemetries = t_result.scalars().all()

    def _stats(attr):
        vals = [getattr(r, attr) for r in telemetries if getattr(r, attr) is not None]
        if not vals:
            return {"avg": None, "min": None, "max": None}
        return {"avg": round(sum(vals) / len(vals), 2), "min": round(min(vals), 2), "max": round(max(vals), 2)}

    w_count = 0
    w_total_ml = 0.0
    w_triggers: list[str] = []
    w_result = await db.execute(
        select(WateringEvent).where(
            WateringEvent.device_id == device_id,
            WateringEvent.timestamp.between(day_start, day_end),
        )
    )
    for event in w_result.scalars().all():
        w_count += 1
        w_total_ml += event.water_pumped_ml or 0
        w_triggers.append(event.trigger)

    p_result = await db.execute(
        select(func.count(Image.image_id)).where(Image.device_id == device_id, Image.timestamp.between(day_start, day_end))
    )
    p_count = p_result.scalar() or 0

    a_result = await db.execute(
        select(func.count(Alert.alert_id)).where(
            Alert.device_id == device_id, Alert.type == "disease_detected",
            Alert.created_at.between(day_start, day_end),
        )
    )
    a_count = a_result.scalar() or 0

    scores_result = await db.execute(
        select(Image.health_score).where(
            Image.device_id == device_id, Image.health_score.isnot(None),
            Image.timestamp.between(day_start, day_end),
        )
    )
    health_scores = [r for r, in scores_result]
    health_score = round(sum(health_scores) / len(health_scores)) if health_scores else None

    from app.services.llm_service import generate_suggestion
    env_data = {
        "temperature": _stats("temperature"),
        "humidity": _stats("humidity"),
        "soil_moisture": _stats("soil_moisture"),
    }
    suggestion, suggestion_detail = generate_suggestion(env_data, w_count, health_score or 100)

    return {
        "date": date_str,
        "environment_summary": env_data,
        "watering": {"count": w_count, "total_ml": round(w_total_ml, 1), "trigger_reasons": list(set(w_triggers))},
        "photos_taken": p_count,
        "disease_alert": a_count > 0,
        "health_score": health_score,
        "suggestion": suggestion,
        "suggestion_detail": suggestion_detail,
    }


async def generate_weekly_report(db: AsyncSession, device_id: str, date_str: str) -> dict:
    ref_date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=UTC)
    week_start = ref_date - timedelta(days=ref_date.weekday())
    week_end = week_start + timedelta(days=6)

    daily_scores = []
    current = week_start
    while current <= week_end:
        day_end_dt = current + timedelta(days=1)
        img_result = await db.execute(
            select(func.avg(Image.health_score), func.count(Image.health_score))
            .where(Image.device_id == device_id, Image.timestamp.between(current, day_end_dt),
                   Image.health_score.isnot(None))
        )
        avg_score, count = img_result.first()
        if count and avg_score:
            daily_scores.append(round(float(avg_score)))
        current += timedelta(days=1)

    avg_health = round(sum(daily_scores) / len(daily_scores)) if daily_scores else None

    prev_start = week_start - timedelta(days=7)
    curr_avg_result = await db.execute(
        select(func.avg(Image.health_score)).where(
            Image.device_id == device_id, Image.timestamp.between(week_start, week_end + timedelta(days=1)),
            Image.health_score.isnot(None),
        )
    )
    prev_avg_result2 = await db.execute(
        select(func.avg(Image.health_score)).where(
            Image.device_id == device_id, Image.timestamp.between(prev_start, week_start),
            Image.health_score.isnot(None),
        )
    )
    curr_avg = curr_avg_result.scalar()
    prev_avg = prev_avg_result2.scalar()
    health_change = round(float(curr_avg - prev_avg), 1) if curr_avg is not None and prev_avg is not None else None

    w_count = 0
    w_total_ml = 0.0
    w_result = await db.execute(
        select(WateringEvent).where(
            WateringEvent.device_id == device_id,
            WateringEvent.timestamp.between(week_start, week_end + timedelta(days=1)),
        )
    )
    for event in w_result.scalars().all():
        w_count += 1
        w_total_ml += event.water_pumped_ml or 0

    prev_w_ml = 0.0
    prev_w_result = await db.execute(
        select(func.coalesce(func.sum(WateringEvent.water_pumped_ml), 0))
        .where(WateringEvent.device_id == device_id, WateringEvent.timestamp.between(prev_start, week_start))
    )
    pw = prev_w_result.scalar()
    if pw is not None:
        prev_w_ml = float(pw)
    watering_change = round(w_total_ml - prev_w_ml, 1)

    a_result = await db.execute(
        select(func.count(Alert.alert_id)).where(
            Alert.device_id == device_id, Alert.type == "disease_detected",
            Alert.created_at.between(week_start, week_end + timedelta(days=1)),
        )
    )
    disease_alerts = a_result.scalar() or 0

    if daily_scores:
        if len(daily_scores) >= 2 and daily_scores[-1] > daily_scores[0]:
            trend = "improving"
        elif len(daily_scores) >= 2 and daily_scores[-1] < daily_scores[0]:
            trend = "declining"
        else:
            trend = "stable"
    else:
        trend = "stable"

    from app.services.llm_service import generate_suggestion
    suggestion, _ = generate_suggestion({}, w_count, avg_health or 100)

    return {
        "week_start": week_start.strftime("%Y-%m-%d"),
        "week_end": week_end.strftime("%Y-%m-%d"),
        "daily_scores": daily_scores,
        "avg_health_score": avg_health,
        "trend": trend,
        "total_watering_count": w_count,
        "total_watering_ml": round(w_total_ml, 1),
        "disease_alert_count": disease_alerts,
        "comparison_with_last_week": {
            "health_score_change": health_change,
            "watering_change_ml": watering_change,
        },
        "suggestion": suggestion,
    }
