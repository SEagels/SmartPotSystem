from __future__ import annotations

from pydantic import BaseModel


class AlertItem(BaseModel):
    alert_id: str
    type: str
    severity: str
    title: str
    message: str
    image_id: str | None = None
    read: bool = False
    created_at: str
