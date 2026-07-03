from __future__ import annotations

from app.adapters.trip_com import TRIP_COM_TRACKING_ID, TripComAffiliateAdapter
from app.models import (
    BookingOption,
    BookingOptionType,
    Itinerary,
    PriceConfidence,
    PriceSourceCoverage,
    SearchRequest,
    Supplier,
)


PRICE_MAY_CHANGE_NOTE = "Price may change at checkout."
TRIP_COM_UNCONFIRMED_NOTE = "Trip.com affiliate/deep-link option only; price must be checked on Trip.com."
SKYSCANNER_UNCONFIGURED_NOTE = "Skyscanner partner API is not configured in this demo."


def _manual_notes(request: SearchRequest) -> list[str]:
    notes: list[str] = []
    if request.promo_code_note:
        notes.append(f"Promo code note: {request.promo_code_note}")
    if request.member_price_note:
        notes.append(f"Member price note: {request.member_price_note}")
    return notes


def build_booking_options(request: SearchRequest, itinerary: Itinerary) -> list[BookingOption]:
    first_offer = itinerary.offers[0]
    notes = [PRICE_MAY_CHANGE_NOTE, *_manual_notes(request)]
    supplier_label = ", ".join(supplier.value for supplier in itinerary.suppliers)
    trip_link = TripComAffiliateAdapter().build_deep_link(
        itinerary.segments[0].origin,
        itinerary.segments[-1].destination,
        request.departure_date,
        request.passengers,
        request.cabin,
        request.currency,
    )
    return [
        BookingOption(
            type=BookingOptionType.airline,
            label="Book with airline",
            supplier=first_offer.supplier,
            url=first_offer.booking_url,
            price_amount=itinerary.total_price,
            currency=itinerary.currency,
            price_confidence=PriceConfidence.confirmed,
            last_checked_at=itinerary.last_checked_at,
            expires_at=itinerary.expires_at,
            notes=notes,
        ),
        BookingOption(
            type=BookingOptionType.trip_com,
            label="Check on Trip.com",
            supplier=Supplier.trip_com_affiliate,
            url=trip_link,
            price_confidence=PriceConfidence.check_required,
            tracking_id=TRIP_COM_TRACKING_ID,
            notes=[TRIP_COM_UNCONFIRMED_NOTE, *notes],
        ),
        BookingOption(
            type=BookingOptionType.skyscanner,
            label="Check on Skyscanner",
            supplier=Supplier.skyscanner,
            price_confidence=PriceConfidence.unavailable,
            notes=[SKYSCANNER_UNCONFIGURED_NOTE, *notes],
        ),
        BookingOption(
            type=BookingOptionType.supplier,
            label="Check on supplier",
            supplier=first_offer.supplier,
            url=first_offer.booking_url,
            price_amount=itinerary.total_price,
            currency=itinerary.currency,
            price_confidence=PriceConfidence.confirmed,
            last_checked_at=itinerary.last_checked_at,
            expires_at=itinerary.expires_at,
            notes=[f"Supplier itinerary source: {supplier_label}.", *notes],
        ),
    ]


def coverage_for_options(options: list[BookingOption]) -> PriceSourceCoverage:
    confirmed = [option for option in options if option.price_confidence == PriceConfidence.confirmed]
    check_required = [
        option for option in options if option.price_confidence == PriceConfidence.check_required
    ]
    unavailable = [option for option in options if option.price_confidence == PriceConfidence.unavailable]
    return PriceSourceCoverage(
        confirmed_supplier_count=len(confirmed),
        check_required_supplier_count=len(check_required),
        unavailable_supplier_count=len(unavailable),
        labels=[option.label for option in options],
    )


def attach_booking_options(request: SearchRequest, itineraries: list[Itinerary]) -> list[Itinerary]:
    updated: list[Itinerary] = []
    for itinerary in itineraries:
        options = build_booking_options(request, itinerary)
        updated.append(itinerary.model_copy(update={
            "booking_options": options,
            "price_source_coverage": coverage_for_options(options),
        }))
    return updated
