"""Configuration utilities for PriceScout."""

from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    """Runtime configuration loaded from environment variables."""

    host: str = "127.0.0.1"
    port: int = 8010
    db_path: str = "pricescout.db"
    request_timeout: int = 10
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    )


def _to_int(value: str | None, default: int) -> int:
    """Convert an environment value to int with a safe fallback."""
    if value is None:
        return default

    try:
        return int(value)
    except ValueError:
        return default


def get_settings() -> Settings:
    """Return application settings loaded from environment variables."""
    return Settings(
        host=os.getenv("PRICESCOUT_HOST", "127.0.0.1"),
        port=_to_int(os.getenv("PRICESCOUT_PORT"), 8010),
        db_path=os.getenv("PRICESCOUT_DB_PATH", "pricescout.db"),
        request_timeout=_to_int(os.getenv("PRICESCOUT_REQUEST_TIMEOUT"), 10),
        user_agent=os.getenv(
            "PRICESCOUT_USER_AGENT",
            (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0.0.0 Safari/537.36"
            ),
        ),
    )
