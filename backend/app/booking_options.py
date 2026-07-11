from __future__ import annotations

from datetime import datetime

from app.booking_security import trusted_booking_url
from app.config import Settings, load_settings
from app.models import (
    BookingOption,
    BookingOptionType,
    Itinerary,
    PriceSourceCoverage,
    PriceStatus,
    SearchRequest,
    Supplier,
    SupplierCapabilities,
)


PRICE_MAY_CHANGE_NOTE = "Price may change at checkout."
UNTRUSTED_URL_NOTE = "The supplier booking URL was not authorised and has been removed."


def _manual_notes(request: SearchRequest) -> list[str]:
    notes: list[str] = []
    if request.promo_code_note:
        notes.append(f"Promo code note: {request.promo_code_note}")
    if request.member_price_note:
        notes.append(f"Member price note: {request.member_price_note}")
    return notes


def build_booking_options(
    request: SearchRequest,
    itinerary: Itinerary,
    supplier_capabilities: dict[Supplier, SupplierCapabilities],
    demo_data: bool,
    settings: Settings,
) -> list[BookingOption]:
    notes = [PRICE_MAY_CHANGE_NOTE, *_manual_notes(request)]
    options: list[BookingOption] = []
    for index, offer in enumerate(itinerary.offers, start=1):
        capabilities = supplier_capabilities.get(offer.supplier, SupplierCapabilities())
        is_expired = offer.expires_at <= datetime.now(offer.expires_at.tzinfo)
        price_status = PriceStatus.unavailable if is_expired else offer.price_status
        canonical_url = trusted_booking_url(
            offer.booking_url, supplier=offer.supplier, settings=settings
        )
        ticket_label = f"Ticket {index}" if len(itinerary.offers) > 1 else "Itinerary"
        warnings = []
        if demo_data:
            warnings.append("Confirmed against deterministic demo data, not a live supplier.")
        if len(itinerary.offers) > 1:
            warnings.append("This ticket is purchased separately from the other segment.")
        warnings.append(PRICE_MAY_CHANGE_NOTE)
        if offer.booking_url is not None and canonical_url is None:
            warnings.append(UNTRUSTED_URL_NOTE)
        options.append(BookingOption(
            id=f"{itinerary.id}:supplier:{index}:{offer.id}",
            type=BookingOptionType.supplier,
            label=(
                f"Verify {ticket_label.lower()} demo price"
                if demo_data
                else f"Verify {ticket_label.lower()} price"
            ),
            display_name=f"{ticket_label} with {offer.supplier.value}",
            supplier=offer.supplier,
            offer_id=offer.id,
            capabilities=capabilities,
            url=canonical_url,
            price_amount=offer.price_amount,
            currency=offer.currency,
            price_status=price_status,
            verification_required=capabilities.supports_price_verify,
            last_checked_at=offer.last_checked_at,
            expires_at=offer.expires_at,
            warnings=warnings,
            notes=notes,
        ))

    return options


def coverage_for_options(options: list[BookingOption]) -> PriceSourceCoverage:
    confirmed = [option for option in options if option.price_status == PriceStatus.confirmed]
    cached = [option for option in options if option.price_status == PriceStatus.cached]
    estimated = [option for option in options if option.price_status == PriceStatus.estimated]
    redirect_only = [option for option in options if option.price_status == PriceStatus.redirect_only]
    check_required = [
        option for option in options
        if option.price_status in {PriceStatus.cached, PriceStatus.estimated, PriceStatus.redirect_only}
    ]
    unavailable = [option for option in options if option.price_status == PriceStatus.unavailable]
    return PriceSourceCoverage(
        confirmed_supplier_count=len(confirmed),
        cached_supplier_count=len(cached),
        estimated_supplier_count=len(estimated),
        redirect_only_supplier_count=len(redirect_only),
        check_required_supplier_count=len(check_required),
        unavailable_supplier_count=len(unavailable),
        labels=[option.label for option in options],
    )


def attach_booking_options(
    request: SearchRequest,
    itineraries: list[Itinerary],
    supplier_capabilities: dict[Supplier, SupplierCapabilities],
    demo_data: bool,
    settings: Settings | None = None,
) -> list[Itinerary]:
    effective_settings = settings or load_settings()
    updated: list[Itinerary] = []
    for itinerary in itineraries:
        options = build_booking_options(
            request, itinerary, supplier_capabilities, demo_data, effective_settings
        )
        updated.append(itinerary.model_copy(update={
            "booking_options": options,
            "price_source_coverage": coverage_for_options(options),
        }))
    return updated
