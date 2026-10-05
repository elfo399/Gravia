from datetime import datetime
from enum import StrEnum
from typing import Literal

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from app.models.api_model import ApiModel, new_id, utc_now


class ActivityType(StrEnum):
    BALANCE_HOLD = "BALANCE_HOLD"
    WEIGHT_SHIFT = "WEIGHT_SHIFT"
    SYMMETRY = "SYMMETRY"


class ActivityStatus(StrEnum):
    WAITING_FOR_USER = "WAITING_FOR_USER"
    COUNTDOWN = "COUNTDOWN"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    ERROR = "ERROR"


ACTIVE_ACTIVITY_STATUSES = [
    ActivityStatus.WAITING_FOR_USER,
    ActivityStatus.COUNTDOWN,
    ActivityStatus.ACTIVE,
]


class ActivitySession(SQLModel, table=True):
    __tablename__ = "activity_sessions"
    id: str = Field(default_factory=new_id, primary_key=True)
    profile_id: str = Field(foreign_key="profiles.id", index=True)
    # Strings deliberately allow future activities without a schema change.
    activity_type: str = Field(index=True)
    status: str = ActivityStatus.WAITING_FOR_USER
    started_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None
    duration_seconds: float
    score: int | None = None
    result_json: dict | None = Field(default=None, sa_column=Column(JSON, nullable=True))
    error_message: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


class ActivityCreate(ApiModel):
    profile_id: str
    activity_type: ActivityType
    duration_seconds: Literal[30] = 30


class ActivityRead(ApiModel):
    id: str
    profile_id: str
    activity_type: str
    status: ActivityStatus
    started_at: datetime
    completed_at: datetime | None
    duration_seconds: float
    score: int | None
    result_json: dict | None
    error_message: str | None
    created_at: datetime
