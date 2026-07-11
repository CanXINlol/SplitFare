from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any

import httpx

from app.adapters.base import SupplierAdapterError


logger = logging.getLogger("splitfare.supplier.http")
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


def stable_supplier_code(status_code: int) -> str:
    if status_code in {401, 403}:
        return "SUPPLIER_AUTH_FAILED"
    if status_code == 429:
        return "SUPPLIER_RATE_LIMITED"
    if status_code == 504:
        return "SUPPLIER_TIMEOUT"
    if status_code >= 500:
        return "SUPPLIER_UNAVAILABLE"
    return "SUPPLIER_INVALID_RESPONSE"


class SupplierHttpClient:
    """Small synchronous server-side client with bounded retries for search and verify calls."""

    def __init__(
        self,
        *,
        base_url: str,
        default_headers: dict[str, str],
        timeout_seconds: float,
        max_retries: int = 1,
        retry_max_delay_seconds: float = 1.0,
        client: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self.base_url = base_url.rstrip("/")
        self.default_headers = dict(default_headers)
        self.timeout_seconds = timeout_seconds
        self.max_retries = max(0, max_retries)
        self.retry_max_delay_seconds = max(0, retry_max_delay_seconds)
        self.client = client or httpx.Client()
        self.sleep = sleep

    def request(
        self,
        method: str,
        path: str,
        *,
        correlation_id: str,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        url = f"{self.base_url}/{path.lstrip('/')}"
        for attempt in range(self.max_retries + 1):
            try:
                response = self.client.request(
                    method,
                    url,
                    headers=self.default_headers,
                    json=json,
                    params=params,
                    timeout=self.timeout_seconds,
                )
            except httpx.TimeoutException as exception:
                raise SupplierAdapterError(
                    "Supplier request timed out.", code="SUPPLIER_TIMEOUT", retryable=True
                ) from exception
            except httpx.HTTPError as exception:
                raise SupplierAdapterError(
                    "Supplier network request failed.", code="SUPPLIER_UNAVAILABLE", retryable=True
                ) from exception

            if response.is_success:
                try:
                    payload = response.json()
                except ValueError as exception:
                    raise SupplierAdapterError(
                        "Supplier returned invalid JSON.", code="SUPPLIER_INVALID_RESPONSE"
                    ) from exception
                if not isinstance(payload, dict):
                    raise SupplierAdapterError(
                        "Supplier response must be a JSON object.", code="SUPPLIER_INVALID_RESPONSE"
                    )
                return payload

            request_id = response.headers.get("x-request-id")
            try:
                error_payload = response.json()
                if isinstance(error_payload, dict):
                    request_id = str(error_payload.get("meta", {}).get("request_id") or request_id or "") or None
            except ValueError:
                error_payload = None
            retryable = response.status_code in RETRYABLE_STATUS_CODES
            if retryable and attempt < self.max_retries:
                reset = response.headers.get("ratelimit-reset") or response.headers.get("retry-after")
                try:
                    delay = min(float(reset or 0), self.retry_max_delay_seconds)
                except ValueError:
                    delay = 0
                if delay > 0:
                    self.sleep(delay)
                logger.info(
                    "supplier.retry correlation_id=%s status=%s attempt=%s request_id=%s",
                    correlation_id, response.status_code, attempt + 1, request_id,
                )
                continue
            raise SupplierAdapterError(
                f"Supplier HTTP {response.status_code}.",
                code=stable_supplier_code(response.status_code),
                retryable=retryable,
                request_id=request_id,
                status_code=response.status_code,
            )
        raise AssertionError("unreachable")
