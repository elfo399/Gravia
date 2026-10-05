from datetime import datetime
from typing import Literal

from app.models.api_model import ApiModel


class BoardStatus(ApiModel):
    mode: Literal["demo", "real"]
    connected: bool
    calibration_active: bool = False
    state: Literal["WAITING_FOR_POWER", "CONNECTING", "CONNECTED", "DISCONNECTING"] | None = None
    mac_address: str | None = None
    last_sample_at: datetime | None = None
    last_error: str | None = None
    battery: int | None = None
