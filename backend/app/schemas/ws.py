from __future__ import annotations

from pydantic import BaseModel


class WSEvent(BaseModel):
    event: str
    device_id: str
    timestamp: str
    payload: dict = {}
