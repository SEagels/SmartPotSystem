from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.alert import Alert
from app.models.image import Image
from app.models.telemetry import Telemetry
from app.models.watering import WateringEvent

logger = logging.getLogger(__name__)

CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "storage", "report_cache")
CACHE_TTL_HOURS = 3


def _data_fingerprint(context: dict) -> str:
    """MD5 hash of key sensor metrics for cache comparison."""
    env = context.get("environment_summary", {})
    key_data = (
        env.get("temperature", {}).get("avg"),
        env.get("humidity", {}).get("avg"),
        env.get("soil_moisture", {}).get("avg"),
        context.get("watering_count", 0),
        context.get("health_score", 100),
        context.get("disease_alert", False),
    )
    return hashlib.md5(str(key_data).encode()).hexdigest()


def _context_changed_significantly(old_ctx: dict, new_ctx: dict) -> bool:
    """Return True if environmental data changed enough to warrant a fresh LLM call."""
    old_env = old_ctx.get("environment_summary", {})
    new_env = new_ctx.get("environment_summary", {})
    for key in ("temperature", "humidity", "soil_moisture"):
        old_avg = old_env.get(key, {}).get("avg")
        new_avg = new_env.get(key, {}).get("avg")
        if old_avg is not None and new_avg is not None:
            if abs(new_avg - old_avg) > 5:
                return True

    if abs(new_ctx.get("watering_count", 0) - old_ctx.get("watering_count", 0)) > 1:
        return True
    if abs(new_ctx.get("health_score", 100) - old_ctx.get("health_score", 100)) > 10:
        return True
    if new_ctx.get("disease_alert") != old_ctx.get("disease_alert"):
        return True

    return False


def _load_cache(device_id: str, date_str: str) -> dict | None:
    cache_path = os.path.join(CACHE_DIR, f"{device_id}_{date_str}.json")
    if not os.path.exists(cache_path):
        return None
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _save_cache(device_id: str, date_str: str, data: dict) -> None:
    os.makedirs(CACHE_DIR, exist_ok=True)
    cache_path = os.path.join(CACHE_DIR, f"{device_id}_{date_str}.json")
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


async def _get_cached_suggestion(
    device_id: str,
    date_str: str,
    llm_context: dict,
) -> tuple[str, dict]:
    """Return cached suggestion if data hasn't changed significantly and TTL not expired."""
    new_fp = _data_fingerprint(llm_context)
    cached = _load_cache(device_id, date_str)

    if cached and cached.get("fingerprint"):
        generated_at = datetime.fromisoformat(cached["generated_at"])
        age_hours = (datetime.now(UTC) - generated_at).total_seconds() / 3600
        if age_hours < CACHE_TTL_HOURS:
            if cached["fingerprint"] == new_fp:
                logger.info("缓存命中(数据相同): device=%s date=%s age=%.1fh", device_id, date_str, age_hours)
                return cached["suggestion"], cached.get("suggestion_detail", {})
            if cached.get("context") and not _context_changed_significantly(cached["context"], llm_context):
                logger.info("缓存命中(数据相近): device=%s date=%s age=%.1fh", device_id, date_str, age_hours)
                return cached["suggestion"], cached.get("suggestion_detail", {})

    from app.services.llm_service import generate_llm_suggestion

    suggestion, suggestion_detail = await generate_llm_suggestion(llm_context)

    _save_cache(device_id, date_str, {
        "fingerprint": new_fp,
        "context": llm_context,
        "suggestion": suggestion,
        "suggestion_detail": suggestion_detail,
        "generated_at": datetime.now(UTC).isoformat(),
    })
    logger.info("缓存已保存: device=%s date=%s", device_id, date_str)
    return suggestion, suggestion_detail


async def generate_daily_report(db: AsyncSession, device_id: str, date_str: str) -> dict:
    day_start = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=UTC)
    day_end = day_start + timedelta(days=1)

    t_result = await db.execute(
        select(Telemetry).where(Telemetry.device_id == device_id, Telemetry.time.between(day_start, day_end))
    )
    telemetries = t_result.scalars().all()

    data_source_date = date_str
    if not telemetries:
        latest_result = await db.execute(
            select(Telemetry).where(Telemetry.device_id == device_id).order_by(Telemetry.time.desc()).limit(1)
        )
        latest = latest_result.scalar_one_or_none()
        if latest:
            latest_day_start = latest.time.replace(hour=0, minute=0, second=0, microsecond=0)
            latest_day_end = latest_day_start + timedelta(days=1)
            fallback_result = await db.execute(
                select(Telemetry).where(
                    Telemetry.device_id == device_id,
                    Telemetry.time.between(latest_day_start, latest_day_end),
                )
            )
            telemetries = fallback_result.scalars().all()
            data_source_date = latest.time.strftime("%Y-%m-%d")
            day_start = latest_day_start
            day_end = latest_day_end

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

    env_data = {
        "temperature": _stats("temperature"),
        "humidity": _stats("humidity"),
        "soil_moisture": _stats("soil_moisture"),
    }
    llm_context = {
        "environment_summary": env_data,
        "watering_count": w_count,
        "health_score": health_score or 100,
        "disease_alert": a_count > 0,
    }
    suggestion, suggestion_detail = await _get_cached_suggestion(device_id, date_str, llm_context)

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

    suggestion, _ = await _get_cached_suggestion(device_id, f"weekly_{date_str}", {
        "watering_count": w_count,
        "health_score": avg_health or 100,
        "trend": trend,
    })

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
