from datetime import datetime
from enum import StrEnum

from sqlmodel import Field, SQLModel

from app.models.api_model import ApiModel, new_id, utc_now


class SessionStatus(StrEnum):
    WAITING_FOR_USER = "WAITING_FOR_USER"
    MEASURING = "MEASURING"
    STABILIZING = "STABILIZING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    ERROR = "ERROR"


ACTIVE_STATUSES = [
    SessionStatus.WAITING_FOR_USER,
    SessionStatus.MEASURING,
    SessionStatus.STABILIZING,
]


class MeasurementSession(SQLModel, table=True):
    __tablename__ = "measurement_sessions"
    id: str = Field(default_factory=new_id, primary_key=True)
    profile_id: str = Field(foreign_key="profiles.id", index=True)
    status: str = SessionStatus.WAITING_FOR_USER
    started_at: datetime = Field(default_factory=utc_now)
    ended_at: datetime | None = None
    error_message: str | None = None


class SessionCreate(ApiModel):
    profile_id: str


class SessionRead(ApiModel):
    id: str
    profile_id: str
    status: SessionStatus
    started_at: datetime
    ended_at: datetime | None
    error_message: str | None
