from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.database import db_write_lock, get_sessionmaker
from app.models.device import Device

logger = logging.getLogger(__name__)
_RUNNING = False


async def start_report_generator():
    global _RUNNING
    _RUNNING = True
    while _RUNNING:
        now = datetime.now(UTC)
        next_midnight = (now + timedelta(days=1)).replace(hour=0, minute=5, second=0, microsecond=0)
        wait_s = (next_midnight - now).total_seconds()
        try:
            await asyncio.sleep(wait_s)
            if _RUNNING:
                await _generate_all_device_reports()
        except asyncio.CancelledError:
            break
        except Exception:
            logger.exception("Report generation failed")


async def stop_report_generator():
    global _RUNNING
    _RUNNING = False


async def _generate_all_device_reports():
    sessionmaker = get_sessionmaker()
    async with db_write_lock:
        async with sessionmaker() as db:
            result = await db.execute(select(Device.device_id, Device.user_id).where(Device.user_id.isnot(None)))
            devices = result.all()

            from app.services.report_service import generate_daily_report
            yesterday = (datetime.now(UTC) - timedelta(days=1)).strftime("%Y-%m-%d")

            for device_id, user_id in devices:
                try:
                    await generate_daily_report(db, device_id, yesterday)
                except Exception:
                    logger.exception(f"Failed to generate report for {device_id}")
