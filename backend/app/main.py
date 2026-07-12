import logging
import time
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.adapters.duffel import DuffelSupplierAdapter
from app.adapters.mock_supplier import MockSupplierAdapter
from app.adapters.orchestrator import SupplierOrchestrator
from app.cache import RedisCache
from app.booking_security import trusted_booking_url
from app.config import Settings, load_settings
from app.db import SessionLocal, init_database
from app.models import (
    CityCatalog,
    PreBookingVerificationRequest,
    PreBookingVerificationResponse,
    PreBookingStatus,
    PriceStatus,
    RouteDiscoveryRequest,
    RouteDiscoveryResponse,
    SearchRequest,
    SearchResponse,
    VerificationStatus,
    VerifyPriceResult,
)
from app.models import Supplier
from app.cities import city_service
from app.repositories import SearchPersistenceService
from app.search import SearchService
from app.search_orchestrator import SearchOrchestrator
from app.route_discovery import discover_routes


settings = load_settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("splitfare.api")

app = FastAPI(
    title="SplitFare API",
    version=settings.app_version,
    debug=not settings.is_production,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.frontend_origins),
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
try:
    init_database()
    database_available = True
except Exception as exception:
    database_available = False
    logger.error("database.initialization_failed reason=%s", type(exception).__name__)
cache = RedisCache.from_env()

_rate_limit_hits: dict[str, list[float]] = {}
_redirect_registry: dict[tuple[str, str, str], tuple[str, datetime]] = {}


def build_supplier_adapters(settings: Settings):
    if settings.enable_mock_supplier and settings.duffel_mode != "disabled":
        raise ValueError("Mock mode cannot be combined with Duffel sandbox or live mode.")
    adapters = [DuffelSupplierAdapter(settings)]
    if settings.enable_mock_supplier:
        adapters.extend([
            MockSupplierAdapter(Supplier.mock_sky),
            MockSupplierAdapter(Supplier.demo_air),
            MockSupplierAdapter(Supplier.budget_demo),
        ])
    return adapters


supplier_orchestrator = SupplierOrchestrator(
    build_supplier_adapters(settings),
    cache=cache,
    max_concurrent_requests=settings.max_concurrent_supplier_requests,
    supplier_timeout_seconds=max(10, settings.external_api_timeout_seconds + 2),
    supplier_mode=settings.app_mode,
)
service = SearchService(
    SearchOrchestrator(
        supplier_orchestrator,
        cache=cache,
        max_supplier_queries_per_search=settings.max_supplier_queries_per_search,
    ),
    persistence_service=SearchPersistenceService(SessionLocal) if database_available else None,
)


def remove_raw_payload(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: remove_raw_payload(item)
            for key, item in value.items()
            if key != "rawPayload"
        }
    if isinstance(value, list):
        return [remove_raw_payload(item) for item in value]
    return value


def error_response(
    *,
    request: Request,
    status_code: int,
    code: str,
    message: str,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "requestId": getattr(request.state, "request_id", None),
            }
        },
    )


@app.middleware("http")
async def request_context_and_rate_limit(request: Request, call_next):
    request.state.request_id = str(uuid4())
    if request.url.path in {"/api/search", "/api/routes/discover"} and request.method == "POST":
        client = request.client.host if request.client else "unknown"
        now = time.monotonic()
        window_start = now - 60
        hits = [item for item in _rate_limit_hits.get(client, []) if item >= window_start]
        if len(hits) >= settings.rate_limit_requests_per_minute:
            return error_response(
                request=request,
                status_code=429,
                code="rate_limited",
                message="Too many search requests. Please wait and try again.",
            )
        hits.append(now)
        _rate_limit_hits[client] = hits
    try:
        response = await call_next(request)
    except Exception as exc:
        logger.exception("unhandled_exception request_id=%s", request.state.request_id)
        return error_response(
            request=request,
            status_code=500,
            code="internal_error",
            message="Internal server error." if settings.is_production else str(exc),
        )
    response.headers["X-Request-ID"] = request.state.request_id
    return response


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    message = str(exc.detail) if exc.detail else "Request failed."
    return error_response(
        request=request,
        status_code=exc.status_code,
        code="http_error",
        message=message,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    message = "Request validation failed."
    if not settings.is_production and exc.errors():
        message = str(exc.errors()[0].get("msg", message))
    return error_response(
        request=request,
        status_code=422,
        code="validation_error",
        message=message,
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled_exception request_id=%s", getattr(request.state, "request_id", None))
    return error_response(
        request=request,
        status_code=500,
        code="internal_error",
        message="Internal server error." if settings.is_production else str(exc),
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "version": settings.app_version,
        "mode": settings.app_mode,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/cities", response_model=CityCatalog)
def city_catalog() -> CityCatalog:
    return city_service.catalog()


@app.post("/api/search", response_model=SearchResponse)
async def search(request: SearchRequest, debug: bool = False) -> JSONResponse:
    try:
        result = await service.search(request)
        payload = result.model_dump(mode="json", by_alias=True)
        allow_debug = debug and not settings.is_production
        return JSONResponse(payload if allow_debug else remove_raw_payload(payload))
    except ValueError as error:
        code = str(error) if str(error) in {"invalid_city_id", "city_has_no_airports"} else "search_invalid"
        raise HTTPException(status_code=422, detail=code) from error


@app.post("/api/routes/discover", response_model=RouteDiscoveryResponse)
def route_discovery(request: RouteDiscoveryRequest) -> RouteDiscoveryResponse:
    try:
        return discover_routes(request)
    except ValueError as error:
        code = str(error) if str(error) in {
            "invalid_city_id", "city_has_no_airports", "airport_coordinates_unavailable"
        } else "route_discovery_invalid"
        raise HTTPException(status_code=422, detail=code) from error


@app.post("/api/offers/{supplier}/{offer_id}/verify", response_model=VerifyPriceResult)
def verify_price(supplier: Supplier, offer_id: str) -> VerifyPriceResult:
    try:
        return supplier_orchestrator.verify_price(supplier, offer_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


def _record_booking_event(
    search_id: str | None, event_type: str, payload: dict[str, Any]
) -> None:
    if not search_id:
        return
    if service.persistence_service is None:
        return
    try:
        service.persistence_service.record_event(search_id, event_type, payload)
    except Exception:
        return


@app.post("/api/booking-options/verify", response_model=PreBookingVerificationResponse)
def verify_booking_option(
    request: PreBookingVerificationRequest,
) -> PreBookingVerificationResponse:
    safe_event = {
        "itinerary_id": request.itinerary_id,
        "booking_option_id": request.booking_option_id,
    }
    _record_booking_event(request.search_id, "booking_option_clicked", safe_event)
    option = service.get_booking_option(
        request.search_id, request.itinerary_id, request.booking_option_id
    )
    if option is None:
        raise HTTPException(
            status_code=404,
            detail="This booking option is unknown or no longer belongs to the selected itinerary.",
        )
    canonical_url = option.booking_url
    previous_price = option.price_amount
    currency = option.currency
    if not option.supports_price_verify:
        response = PreBookingVerificationResponse(
            booking_option_id=option.id,
            still_available=canonical_url is not None,
            current_price=None,
            previous_price=previous_price,
            currency=currency,
            price_changed=False,
            booking_url=canonical_url,
            checked_at=datetime.now(timezone.utc),
            status=PreBookingStatus.unsupported,
            message="VERIFY_UNSUPPORTED",
            can_continue=canonical_url is not None,
            requires_price_check=True,
        )
    else:
        _record_booking_event(request.search_id, "verification_started", safe_event)
        if option.supplier is None or option.offer_id is None:
            response = PreBookingVerificationResponse(
                booking_option_id=option.id,
                still_available=False,
                current_price=None,
                previous_price=previous_price,
                currency=currency,
                price_changed=False,
                booking_url=None,
                checked_at=datetime.now(timezone.utc),
                status=PreBookingStatus.unavailable,
                message="VERIFY_UNAVAILABLE",
                can_continue=False,
            )
        else:
            try:
                verification = supplier_orchestrator.verify_price(option.supplier, option.offer_id)
            except TimeoutError:
                verification = VerifyPriceResult(
                    offer_id=option.offer_id,
                    supplier=option.supplier,
                    status=VerificationStatus.timeout,
                    supported=True,
                    checked_at=datetime.now(timezone.utc),
                    message="Price verification timed out. Try again before continuing.",
                )
            still_available = (
                verification.status == VerificationStatus.verified
                and verification.price_status == PriceStatus.confirmed
                and verification.is_confirmed
            )
            current_price = verification.price_amount if still_available else None
            currency = verification.currency or currency
            if still_available and current_price is not None and previous_price is not None:
                if current_price > previous_price + Decimal("0.01"):
                    status = PreBookingStatus.increased
                elif current_price < previous_price - Decimal("0.01"):
                    status = PreBookingStatus.decreased
                else:
                    status = PreBookingStatus.unchanged
            elif verification.status == VerificationStatus.expired:
                status = PreBookingStatus.expired
            elif verification.status == VerificationStatus.timeout:
                status = PreBookingStatus.timeout
            elif verification.status == VerificationStatus.unsupported:
                status = PreBookingStatus.unsupported
            else:
                status = PreBookingStatus.unavailable
            price_changed = status in {
                PreBookingStatus.increased, PreBookingStatus.decreased
            }
            response = PreBookingVerificationResponse(
                booking_option_id=option.id,
                still_available=still_available,
                current_price=current_price,
                previous_price=previous_price,
                currency=currency,
                price_changed=price_changed,
                booking_url=canonical_url if still_available else None,
                checked_at=verification.checked_at,
                expires_at=verification.expires_at,
                status=status,
                message=f"VERIFY_{status.value.upper()}",
                can_continue=still_available and canonical_url is not None,
            )

    if response.can_continue and response.booking_url is not None:
        expiry = response.expires_at or datetime.now(timezone.utc) + timedelta(minutes=10)
        _redirect_registry[(request.search_id, request.itinerary_id, option.id)] = (
            str(response.booking_url), expiry
        )
    if response.status in {PreBookingStatus.unchanged}:
        event_type = "verification_succeeded"
    elif response.status in {PreBookingStatus.increased, PreBookingStatus.decreased}:
        event_type = "verification_changed"
    else:
        event_type = "verification_failed"
    _record_booking_event(
        request.search_id,
        event_type,
        {**safe_event, "status": response.status.value},
    )
    return response


@app.post("/api/booking-options/redirect-confirmed")
def confirm_provider_redirect(request: PreBookingVerificationRequest) -> dict[str, str]:
    option = service.get_booking_option(
        request.search_id, request.itinerary_id, request.booking_option_id
    )
    key = (request.search_id, request.itinerary_id, request.booking_option_id)
    registered = _redirect_registry.get(key)
    if option is None or registered is None:
        raise HTTPException(status_code=409, detail="booking_redirect_not_verified")
    registered_url, expires_at = registered
    canonical_url = trusted_booking_url(
        option.booking_url, supplier=option.supplier, settings=settings
    ) if option.supplier is not None else None
    if (
        canonical_url is None
        or str(canonical_url) != registered_url
        or expires_at <= datetime.now(timezone.utc)
    ):
        _redirect_registry.pop(key, None)
        raise HTTPException(status_code=409, detail="booking_redirect_expired")
    _record_booking_event(
        request.search_id,
        "provider_redirect_confirmed",
        {
            "itinerary_id": request.itinerary_id,
            "booking_option_id": request.booking_option_id,
            "supplier": option.supplier.value,
        },
    )
    return {"bookingUrl": registered_url}
