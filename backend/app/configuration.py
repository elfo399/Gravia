import re
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GRAVIA_", env_file=".env", extra="ignore")

    board_mode: Literal["demo", "real"] = "demo"
    # Backwards-compatible default; select bluez explicitly after the host installation.
    board_transport: Literal["bluez", "direct"] = "direct"
    board_socket: str = "/run/gravia/balance-board.sock"
    board_mac: str = ""
    board_sample_timeout: float = Field(default=2, gt=0)
    database_url: str = "sqlite:///./gravia.db"
    minimum_weight: float = Field(default=20, gt=0)
    required_stability: float = Field(default=95, ge=1, le=100)
    stability_range_kg: float = Field(default=0.8, gt=0)
    stability_stddev_kg: float = Field(default=0.3, gt=0)
    stable_duration: float = Field(default=2.5, gt=0)
    session_timeout: float = Field(default=60, gt=0)
    demo_seed: bool = True
    frontend_directory: str = "../frontend/dist"

    @field_validator("board_mac")
    @classmethod
    def validate_mac(cls, value: str) -> str:
        value = value.strip().upper()
        if value and not re.fullmatch(r"(?:[0-9A-F]{2}:){5}[0-9A-F]{2}", value):
            raise ValueError(
                "GRAVIA_BOARD_MAC must be a Bluetooth MAC address (AA:BB:CC:DD:EE:FF)."
            )
        return value

    @model_validator(mode="after")
    def require_real_board_mac(self):
        if self.board_mode == "real" and not self.board_mac:
            raise ValueError("GRAVIA_BOARD_MAC is required when GRAVIA_BOARD_MODE=real.")
        return self
