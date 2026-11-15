"""Chaos switch — optional random 503 for judge resilience checks."""

from __future__ import annotations

import random

from fastapi import HTTPException, Request

from app.config import settings


def maybe_chaos(request: Request) -> None:
    """Raise 503 when SPECTAC_CHAOS=1 and random draw hits fail rate.

    Bypass with header X-Spectac-Chaos: off (useful for tests / demos).
    """
    if not settings.chaos_enabled:
        return
    if request.headers.get("X-Spectac-Chaos", "").lower() in {"off", "0", "false"}:
        return
    if random.random() < settings.chaos_fail_rate:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "chaos_injected",
                "message": "Transient failure (chaos switch). Retry.",
            },
        )
