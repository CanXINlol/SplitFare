from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.adapters.duffel import DuffelSupplierAdapter
from app.adapters.mock_supplier import MockSupplierAdapter
from app.adapters.orchestrator import SupplierOrchestrator
from app.adapters.trip_com import TripComAffiliateAdapter
from app.cache import RedisCache
from app.config import Settings, load_settings
from app.db import SessionLocal, init_database
from app.models import (
    BookingOptionType,
    PreBookingVerificationRequest,
    PreBookingVerificationResponse,
    PriceVerification,
    SearchRequest,
    SearchResponse,
    VerificationStatus,
)
from app.models import Supplier
from app.repositories import SearchPersistenceService
from app.search import SearchService
from app.search_orchestrator import SearchOrchestrator

app = FastAPI(title="SplitFare Mock API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3010",
        "http://127.0.0.1:3010",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
init_database()
settings = load_settings()
cache = RedisCache.from_env()


def build_supplier_adapters(settings: Settings):
    adapters = [
        MockSupplierAdapter(Supplier.mock_sky),
        MockSupplierAdapter(Supplier.demo_air),
        MockSupplierAdapter(Supplier.budget_demo),
        TripComAffiliateAdapter(),
    ]
    if settings.duffel_enabled:
        adapters.append(DuffelSupplierAdapter(settings))
    return adapters


supplier_orchestrator = SupplierOrchestrator(build_supplier_adapters(settings), cache=cache)
service = SearchService(
    SearchOrchestrator(supplier_orchestrator, cache=cache),
    persistence_service=SearchPersistenceService(SessionLocal),
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


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/search", response_model=SearchResponse)
async def search(request: SearchRequest, debug: bool = False) -> JSONResponse:
    try:
        result = await service.search(request)
        payload = result.model_dump(mode="json", by_alias=True)
        return JSONResponse(payload if debug else remove_raw_payload(payload))
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.post("/api/offers/{supplier}/{offer_id}/verify", response_model=PriceVerification)
def verify_price(supplier: Supplier, offer_id: str) -> PriceVerification:
    try:
        return supplier_orchestrator.verify_price(supplier, offer_id)
    except ValueError as error:
        if supplier == Supplier.duffel:
            return DuffelSupplierAdapter(settings).verify_price(offer_id)
        raise HTTPException(status_code=404, detail=str(error)) from error


def _record_booking_event(
    search_id: str | None, event_type: str, payload: dict[str, Any]
) -> None:
    if not search_id:
        return
    try:
        service.persistence_service.record_event(search_id, event_type, payload)  # type: ignore[union-attr]
    except Exception:
        return


def _verify_supplier_price(
    supplier: Supplier, offer_id: str | None
) -> PriceVerification | None:
    if not offer_id:
        return None
    try:
        return supplier_orchestrator.verify_price(supplier, offer_id)
    except ValueError:
        if supplier == Supplier.duffel:
            return DuffelSupplierAdapter(settings).verify_price(offer_id)
        return None


@app.post("/api/booking-options/verify", response_model=PreBookingVerificationResponse)
def verify_booking_option(
    request: PreBookingVerificationRequest,
) -> PreBookingVerificationResponse:
    click_payload = request.model_dump(mode="json")
    _record_booking_event(request.search_id, "booking.clicked", click_payload)

    if request.booking_option_type == BookingOptionType.trip_com:
        response = PreBookingVerificationResponse(
            still_available=bool(request.booking_url),
            current_price=None,
            previous_price=request.previous_price,
            currency=request.currency,
            price_changed=False,
            booking_url=request.booking_url,
            checked_at=datetime.now(timezone.utc),
            status=VerificationStatus.unavailable,
            message=(
                "Trip.com affiliate/deep-link prices are not confirmed. "
                "Continue only to check the current price on Trip.com."
            ),
            can_continue=bool(request.booking_url),
            requires_price_check=True,
        )
    else:
        verification = _verify_supplier_price(request.supplier, request.offer_id)
        if verification is None:
            response = PreBookingVerificationResponse(
                still_available=False,
                current_price=None,
                previous_price=request.previous_price,
                currency=request.currency,
                price_changed=False,
                booking_url=None,
                checked_at=datetime.now(timezone.utc),
                status=VerificationStatus.unavailable,
                message="This booking option cannot be verified right now.",
                can_continue=False,
            )
        else:
            still_available = verification.status == VerificationStatus.verified and verification.is_confirmed
            current_price = verification.price_amount if still_available else None
            currency = verification.currency or request.currency
            price_changed = (
                current_price is not None
                and request.previous_price is not None
                and abs(current_price - request.previous_price) > 0.01
            )
            response = PreBookingVerificationResponse(
                still_available=still_available,
                current_price=current_price,
                previous_price=request.previous_price,
                currency=currency,
                price_changed=price_changed,
                booking_url=request.booking_url if still_available else None,
                checked_at=verification.checked_at,
                expires_at=verification.expires_at,
                status=verification.status,
                message=verification.message if still_available else "Price or availability could not be confirmed.",
                can_continue=still_available and request.booking_url is not None,
            )

    _record_booking_event(request.search_id, "booking.verification_completed", response.model_dump(mode="json"))
    return response
