from datetime import datetime
from typing import Literal

from app.models.api_model import ApiModel


class BoardStatus(ApiModel):
    mode: Literal["demo", "real"]
    connected: bool
    mac_address: str | None = None
    last_sample_at: datetime | None = None
    last_error: str | None = None
    battery: int | None = None
