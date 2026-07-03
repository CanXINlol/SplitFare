from __future__ import annotations

import os
from dataclasses import dataclass

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - dotenv is optional outside local dev.
    load_dotenv = None


def _float_env(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return float(value)


@dataclass(frozen=True)
class Settings:
    duffel_api_token: str | None = None
    duffel_base_url: str = "https://api.duffel.com"
    duffel_api_version: str = "v2"
    external_api_timeout_seconds: float = 10.0

    @property
    def duffel_enabled(self) -> bool:
        return bool(self.duffel_api_token)


def load_settings() -> Settings:
    if load_dotenv is not None:
        load_dotenv()
    token = os.getenv("DUFFEL_API_TOKEN")
    return Settings(
        duffel_api_token=token.strip() if token and token.strip() else None,
        duffel_base_url=os.getenv("DUFFEL_BASE_URL", "https://api.duffel.com").rstrip("/"),
        duffel_api_version=os.getenv("DUFFEL_API_VERSION", "v2"),
        external_api_timeout_seconds=_float_env("EXTERNAL_API_TIMEOUT_SECONDS", 10.0),
    )
