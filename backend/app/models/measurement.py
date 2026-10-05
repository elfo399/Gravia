from datetime import datetime

from pydantic import Field as InputField
from sqlmodel import Field, SQLModel

from app.models.api_model import ApiModel, new_id, utc_now


class Measurement(SQLModel, table=True):
    __tablename__ = "measurements"
    id: str = Field(default_factory=new_id, primary_key=True)
    session_id: str = Field(foreign_key="measurement_sessions.id", unique=True)
    profile_id: str = Field(foreign_key="profiles.id", index=True)
    weight: float
    front_left: float
    front_right: float
    rear_left: float
    rear_right: float
    center_x: float
    center_y: float
    stability: float
    measured_at: datetime = Field(default_factory=utc_now, index=True)
    created_at: datetime = Field(default_factory=utc_now)
    notes: str | None = None


class MeasurementRead(ApiModel):
    id: str
    session_id: str
    profile_id: str
    weight: float
    front_left: float
    front_right: float
    rear_left: float
    rear_right: float
    center_x: float
    center_y: float
    stability: float
    measured_at: datetime
    created_at: datetime
    notes: str | None


class MeasurementUpdate(ApiModel):
    notes: str | None = InputField(default=None, max_length=1000)
