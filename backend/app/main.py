import logging
import time
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.adapters.duffel import DuffelSupplierAdapter
from app.adapters.mock_supplier import MockSupplierAdapter
from app.adapters.orchestrator import SupplierOrchestrator
from app.adapters.trip_com import TripComAffiliateAdapter
from app.adapters.skyscanner import SkyscannerSupplierAdapter
from app.cache import RedisCache
from app.config import Settings, load_settings
from app.db import SessionLocal, init_database
from app.models import (
    PlaceSearchResponse,
    PreBookingVerificationRequest,
    PreBookingVerificationResponse,
    PriceStatus,
    ResolvePlaceRequest,
    ResolvedPlace,
    SearchRequest,
    SearchResponse,
    VerificationStatus,
    VerifyPriceResult,
)
from app.models import Supplier
from app.places import place_service
from app.repositories import SearchPersistenceService
from app.search import SearchService
from app.search_orchestrator import SearchOrchestrator


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


def build_supplier_adapters(settings: Settings):
    duffel_settings = replace(settings, duffel_api_token=None) if settings.enable_mock_supplier else settings
    adapters = [
        TripComAffiliateAdapter(),
        SkyscannerSupplierAdapter(),
        DuffelSupplierAdapter(duffel_settings),
    ]
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
    if request.url.path == "/api/search" and request.method == "POST":
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


@app.get("/api/places/search", response_model=PlaceSearchResponse)
def search_places(q: str = Query(min_length=1, max_length=80)) -> PlaceSearchResponse:
    return PlaceSearchResponse(results=place_service.search(q))


@app.post("/api/places/resolve", response_model=ResolvedPlace)
def resolve_place(request: ResolvePlaceRequest) -> ResolvedPlace:
    try:
        return place_service.resolve(request.place_id)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.post("/api/search", response_model=SearchResponse)
async def search(request: SearchRequest, debug: bool = False) -> JSONResponse:
    try:
        result = await service.search(request)
        payload = result.model_dump(mode="json", by_alias=True)
        allow_debug = debug and not settings.is_production
        return JSONResponse(payload if allow_debug else remove_raw_payload(payload))
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


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
    click_payload = request.model_dump(mode="json")
    _record_booking_event(request.search_id, "booking.clicked", click_payload)
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
    if not option.capabilities.supports_price_verify:
        response = PreBookingVerificationResponse(
            still_available=canonical_url is not None,
            current_price=None,
            previous_price=previous_price,
            currency=currency,
            price_changed=False,
            booking_url=canonical_url,
            checked_at=datetime.now(timezone.utc),
            status=VerificationStatus.unsupported,
            message="This provider does not support price verification in SplitFare. Check the final price on the provider.",
            can_continue=canonical_url is not None,
            requires_price_check=True,
        )
    else:
        if option.supplier is None or option.offer_id is None:
            response = PreBookingVerificationResponse(
                still_available=False,
                current_price=None,
                previous_price=previous_price,
                currency=currency,
                price_changed=False,
                booking_url=None,
                checked_at=datetime.now(timezone.utc),
                status=VerificationStatus.unavailable,
                message="This booking option cannot be verified right now.",
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
            price_changed = (
                current_price is not None
                and previous_price is not None
                and abs(current_price - previous_price) > Decimal("0.01")
            )
            response = PreBookingVerificationResponse(
                still_available=still_available,
                current_price=current_price,
                previous_price=previous_price,
                currency=currency,
                price_changed=price_changed,
                booking_url=canonical_url if still_available else None,
                checked_at=verification.checked_at,
                expires_at=verification.expires_at,
                status=verification.status,
                message=verification.message if still_available else verification.message,
                can_continue=still_available and canonical_url is not None,
            )

    _record_booking_event(request.search_id, "booking.verification_completed", response.model_dump(mode="json"))
    return response
