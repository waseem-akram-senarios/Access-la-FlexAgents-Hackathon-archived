"""Runtime config for Spectac Track B APIs."""

from __future__ import annotations

import os
from dataclasses import dataclass
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class Settings:
    app_name: str = "Spectac Track B APIs"
    timezone: str = "America/Los_Angeles"
    chaos_enabled: bool = False
    chaos_fail_rate: float = 0.15
    host: str = "0.0.0.0"
    port: int = 8787

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)


def load_settings() -> Settings:
    return Settings(
        chaos_enabled=os.getenv("SPECTAC_CHAOS", "0").strip() in {"1", "true", "TRUE", "yes"},
        chaos_fail_rate=float(os.getenv("SPECTAC_CHAOS_RATE", "0.15")),
        host=os.getenv("SPECTAC_HOST", "0.0.0.0"),
        port=int(os.getenv("SPECTAC_PORT", "8787")),
        timezone=os.getenv("SPECTAC_TZ", "America/Los_Angeles"),
    )


settings = load_settings()
