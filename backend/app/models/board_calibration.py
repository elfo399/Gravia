from datetime import datetime
from typing import Literal

from pydantic import ConfigDict
from pydantic import Field as ApiField
from sqlmodel import Field, SQLModel

from app.models.api_model import ApiModel, new_id, utc_now


class BoardCalibration(SQLModel, table=True):
    __tablename__ = "board_calibrations"

    id: str = Field(default_factory=new_id, primary_key=True)
    board_mac: str = Field(unique=True)
    front_left_offset: float
    front_right_offset: float
    rear_left_offset: float
    rear_right_offset: float
    weight_scale: float
    reference_weight: float
    measured_weight_before: float
    measured_weight_after: float
    calibrated_at: datetime = Field(default_factory=utc_now)


class BoardCalibrationRead(ApiModel):
    board_mac: str
    front_left_offset: float
    front_right_offset: float
    rear_left_offset: float
    rear_right_offset: float
    weight_scale: float
    reference_weight: float
    measured_weight_before: float
    measured_weight_after: float
    calibrated_at: datetime


class CalibrationSessionRead(ApiModel):
    id: str
    stage: Literal["TARE", "REFERENCE", "VERIFY"]
    busy: bool = False
    reference_weight: float | None = None
    weight_scale: float | None = None
    measured_weight_before: float | None = None
    measured_weight_after: float | None = None
    absolute_error: float | None = None
    percentage_error: float | None = None
    valid: bool | None = None


class BoardCalibrationStatus(ApiModel):
    configured: bool
    calibration: BoardCalibrationRead | None = None
    active_session: CalibrationSessionRead | None = None


class ReferenceWeight(ApiModel):
    model_config = ConfigDict(extra="forbid")
    reference_weight: float = ApiField(gt=0, le=150, allow_inf_nan=False)


class CalibrationCommand(ApiModel):
    model_config = ConfigDict(extra="forbid")
