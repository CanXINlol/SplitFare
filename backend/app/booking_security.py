from __future__ import annotations

from pydantic import HttpUrl, TypeAdapter, ValidationError

from app.config import Settings
from app.models import Supplier


BLOCKED_HOSTS = {"example.com", "www.example.com", "example.invalid"}
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


def _host_matches(host: str, allowed: str) -> bool:
    allowed = allowed.lower().strip().lstrip(".")
    return bool(allowed) and (host == allowed or host.endswith(f".{allowed}"))


def trusted_booking_url(
    value: HttpUrl | str | None,
    *,
    supplier: Supplier,
    settings: Settings,
) -> HttpUrl | None:
    """Return a canonical supplier URL only when its scheme and host are authorised."""
    if value is None:
        return None
    if isinstance(value, str):
        try:
            value = TypeAdapter(HttpUrl).validate_python(value)
        except ValidationError:
            return None
    host = (value.host or "").lower()
    if host in BLOCKED_HOSTS or host.endswith(".example.com"):
        return None
    if value.scheme == "http":
        return value if not settings.is_production and host in LOCAL_HOSTS else None
    if value.scheme != "https":
        return None
    allowed_domains = (
        settings.duffel_booking_allowed_domains if supplier == Supplier.duffel else ()
    )
    return value if any(_host_matches(host, domain) for domain in allowed_domains) else None
