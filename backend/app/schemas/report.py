from __future__ import annotations

from pydantic import BaseModel, Field


class DailyReportResponse(BaseModel):
    date: str
    environment_summary: dict = Field(default_factory=dict)
    watering: dict = Field(default_factory=dict)
    photos_taken: int = 0
    disease_alert: bool = False
    health_score: int = 100
    suggestion: str = ""
    suggestion_detail: dict = Field(default_factory=dict)


class WeeklyReportResponse(BaseModel):
    week_start: str
    week_end: str
    daily_scores: list[int] = Field(default_factory=list)
    avg_health_score: float = 0
    trend: str = "stable"
    total_watering_count: int = 0
    total_watering_ml: float = 0
    disease_alert_count: int = 0
    comparison_with_last_week: dict = Field(default_factory=dict)
    suggestion: str = ""
