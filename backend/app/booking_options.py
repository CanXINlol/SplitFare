from __future__ import annotations

from app.adapters.trip_com import TRIP_COM_TRACKING_ID, TripComAffiliateAdapter
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
TRIP_COM_UNCONFIRMED_NOTE = "Trip.com redirect only; SplitFare cannot confirm its price."
SKYSCANNER_UNCONFIGURED_NOTE = "Skyscanner is a redirect-only option in this demo."
SKYSCANNER_REDIRECT_URL = "https://www.skyscanner.com/transport/flights/"


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
) -> list[BookingOption]:
    notes = [PRICE_MAY_CHANGE_NOTE, *_manual_notes(request)]
    options: list[BookingOption] = []
    for index, offer in enumerate(itinerary.offers, start=1):
        capabilities = supplier_capabilities.get(offer.supplier, SupplierCapabilities())
        is_expired = offer.expires_at <= offer.last_checked_at or itinerary.price_freshness.is_expired
        is_cached = offer.price_status == PriceStatus.cached or is_expired
        ticket_label = f"Ticket {index}" if len(itinerary.offers) > 1 else "Itinerary"
        warnings = []
        if demo_data:
            warnings.append("Confirmed against deterministic demo data, not a live supplier.")
        if len(itinerary.offers) > 1:
            warnings.append("This ticket is purchased separately from the other segment.")
        warnings.append(PRICE_MAY_CHANGE_NOTE)
        options.append(BookingOption(
            id=f"{itinerary.id}:supplier:{index}:{offer.id}",
            type=BookingOptionType.supplier,
            label=f"Verify {ticket_label.lower()} demo price" if demo_data else f"Book {ticket_label.lower()}",
            display_name=f"{ticket_label} with {offer.supplier.value}",
            supplier=offer.supplier,
            offer_id=offer.id,
            capabilities=capabilities,
            url=offer.booking_url,
            price_amount=offer.price_amount,
            currency=offer.currency,
            price_status=PriceStatus.cached if is_cached else PriceStatus.confirmed,
            verification_required=capabilities.supports_price_verify,
            last_checked_at=offer.last_checked_at,
            expires_at=offer.expires_at,
            warnings=warnings,
            notes=notes,
        ))

    trip_capabilities = supplier_capabilities.get(
        Supplier.trip_com_affiliate,
        SupplierCapabilities(supports_booking_url=True, supports_affiliate_link=True),
    )
    skyscanner_capabilities = supplier_capabilities.get(
        Supplier.skyscanner,
        SupplierCapabilities(supports_booking_url=True, supports_affiliate_link=True),
    )
    trip_link = TripComAffiliateAdapter().build_deep_link(
        itinerary.segments[0].origin,
        itinerary.segments[-1].destination,
        request.departure_date,
        request.passengers,
        request.cabin,
        request.currency,
    )
    options.extend([
        BookingOption(
            id=f"{itinerary.id}:trip-com",
            type=BookingOptionType.trip_com,
            label="Check on Trip.com",
            display_name="Check on Trip.com",
            supplier=Supplier.trip_com_affiliate,
            capabilities=trip_capabilities,
            url=trip_link,
            price_status=PriceStatus.redirect_only,
            verification_required=False,
            tracking_id=TRIP_COM_TRACKING_ID,
            warnings=[TRIP_COM_UNCONFIRMED_NOTE, PRICE_MAY_CHANGE_NOTE],
            notes=[TRIP_COM_UNCONFIRMED_NOTE, *notes],
        ),
        BookingOption(
            id=f"{itinerary.id}:skyscanner",
            type=BookingOptionType.skyscanner,
            label="Check on Skyscanner",
            display_name="Check on Skyscanner",
            supplier=Supplier.skyscanner,
            capabilities=skyscanner_capabilities,
            url=SKYSCANNER_REDIRECT_URL,
            price_status=PriceStatus.redirect_only,
            verification_required=False,
            warnings=[SKYSCANNER_UNCONFIGURED_NOTE, PRICE_MAY_CHANGE_NOTE],
            notes=[SKYSCANNER_UNCONFIGURED_NOTE, *notes],
        ),
    ])
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
) -> list[Itinerary]:
    updated: list[Itinerary] = []
    for itinerary in itineraries:
        options = build_booking_options(request, itinerary, supplier_capabilities, demo_data)
        updated.append(itinerary.model_copy(update={
            "booking_options": options,
            "price_source_coverage": coverage_for_options(options),
        }))
    return updated
