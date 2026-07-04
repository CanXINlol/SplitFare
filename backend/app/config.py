from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - dotenv is optional outside local dev.
    load_dotenv = None


def _float_env(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return float(value)


def _int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return int(value)


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _csv_env(name: str, default: tuple[str, ...]) -> tuple[str, ...]:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return tuple(item.strip().rstrip("/") for item in value.split(",") if item.strip())


@dataclass(frozen=True)
class Settings:
    app_env: str = "local"
    app_version: str = "0.1.0"
    api_base_url: str = "http://localhost:8000"
    frontend_origins: tuple[str, ...] = (
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3010",
        "http://127.0.0.1:3010",
        "http://localhost:8081",
        "http://127.0.0.1:8081",
    )
    enable_mock_supplier: bool = True
    log_level: str = "INFO"
    rate_limit_requests_per_minute: int = 120
    duffel_api_token: str | None = None
    duffel_base_url: str = "https://api.duffel.com"
    duffel_api_version: str = "v2"
    external_api_timeout_seconds: float = 10.0

    @property
    def duffel_enabled(self) -> bool:
        return bool(self.duffel_api_token)

    @property
    def app_mode(self) -> Literal["mock", "live"]:
        return "mock" if self.enable_mock_supplier else "live"

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() in {"production", "prod"}


def load_settings() -> Settings:
    if load_dotenv is not None:
        load_dotenv()
    token = os.getenv("DUFFEL_API_TOKEN")
    app_env = os.getenv("APP_ENV", "local").strip() or "local"
    local_origins = (
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3010",
        "http://127.0.0.1:3010",
        "http://localhost:8081",
        "http://127.0.0.1:8081",
    )
    return Settings(
        app_env=app_env,
        app_version=os.getenv("APP_VERSION", "0.1.0").strip() or "0.1.0",
        api_base_url=os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/"),
        frontend_origins=_csv_env(
            "FRONTEND_ORIGIN",
            local_origins if app_env.lower() not in {"production", "prod"} else (),
        ),
        enable_mock_supplier=_bool_env("ENABLE_MOCK_SUPPLIER", True),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        rate_limit_requests_per_minute=_int_env("RATE_LIMIT_REQUESTS_PER_MINUTE", 120),
        duffel_api_token=token.strip() if token and token.strip() else None,
        duffel_base_url=os.getenv("DUFFEL_BASE_URL", "https://api.duffel.com").rstrip("/"),
        duffel_api_version=os.getenv("DUFFEL_API_VERSION", "v2"),
        external_api_timeout_seconds=_float_env("EXTERNAL_API_TIMEOUT_SECONDS", 10.0),
    )
