from datetime import datetime

from pydantic import Field as InputField
from sqlmodel import Field, SQLModel

from app.models.api_model import ApiModel, new_id, utc_now


class Profile(SQLModel, table=True):
    __tablename__ = "profiles"
    id: str = Field(default_factory=new_id, primary_key=True)
    name: str
    height_cm: float | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ProfileCreate(ApiModel):
    name: str = InputField(min_length=1, max_length=80, pattern=r"\S")
    height_cm: float | None = InputField(default=None, ge=50, le=250)


class ProfileUpdate(ApiModel):
    name: str | None = InputField(default=None, min_length=1, max_length=80, pattern=r"\S")
    height_cm: float | None = InputField(default=None, ge=50, le=250)


class ProfileRead(ProfileCreate):
    id: str
    created_at: datetime
    updated_at: datetime
