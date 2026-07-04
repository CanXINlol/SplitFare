import asyncio
from datetime import date

import pytest
from pydantic import ValidationError

from app.adapters.mock_supplier import build_mock_orchestrator
from app.adapters.trip_com import TRIP_COM_TRACKING_ID, TripComAffiliateAdapter
from app.models import (
    BookingOption,
    BookingOptionType,
    PriceConfidence,
    PriceStatus,
    SearchRequest,
    Supplier,
)
from app.search import SearchService
from app.search_orchestrator import SearchOrchestrator


def request(**updates) -> SearchRequest:
    data = {
        "origin": "MEL",
        "destination": "PVG",
        "departureDate": date(2026, 8, 12),
        "minGapHours": 3,
        "maxGapHours": 12,
        "passengers": 1,
        "cabin": "economy",
    } | updates
    return SearchRequest(**data)


def search(search_request: SearchRequest):
    service = SearchService(SearchOrchestrator(build_mock_orchestrator()))
    return asyncio.run(service.search(search_request))


def test_trip_com_booking_option_is_returned_with_tracking_id_and_unconfirmed_price() -> None:
    response = search(request())
    trip_options = [
        option
        for itinerary in response.ranked_results
        for option in itinerary.booking_options
        if option.type == BookingOptionType.trip_com
    ]
    assert trip_options
    assert all(option.label == "Check on Trip.com" for option in trip_options)
    assert all(option.tracking_id == TRIP_COM_TRACKING_ID for option in trip_options)
    assert all(option.price_confidence == PriceConfidence.check_required for option in trip_options)
    assert all(option.price_status == PriceStatus.redirect_only for option in trip_options)
    assert all(option.price_amount is None for option in trip_options)
    assert all("tracking_id=SPLITFARE_PLACEHOLDER" in str(option.url) for option in trip_options)


def test_skyscanner_booking_option_is_redirect_only() -> None:
    response = search(request())
    options = [
        option
        for itinerary in response.ranked_results
        for option in itinerary.booking_options
        if option.type == BookingOptionType.skyscanner
    ]
    assert options
    assert all(option.price_status == PriceStatus.redirect_only for option in options)
    assert all(option.price_amount is None for option in options)
    assert all(option.verification_required for option in options)


def test_mock_supplier_booking_option_has_confirmed_price_status() -> None:
    response = search(request())
    supplier_options = [
        option
        for itinerary in response.ranked_results
        for option in itinerary.booking_options
        if option.type == BookingOptionType.supplier
    ]
    assert supplier_options
    assert all(option.price_status == PriceStatus.confirmed for option in supplier_options)
    assert all(option.price_amount is not None for option in supplier_options)


def test_trip_com_deep_link_does_not_create_fare_offers_or_affect_sorting() -> None:
    response = search(request(sort="cheapest"))
    cheapest_before_options = response.ranked_results[0].total_price
    assert TripComAffiliateAdapter().search_one_way(
        "MEL", "PVG", date(2026, 8, 12), 1, request().cabin, "AUD"
    ) == []
    assert response.ranked_results[0].total_price == cheapest_before_options
    assert all(
        offer.supplier != Supplier.trip_com_affiliate
        for itinerary in response.ranked_results
        for offer in itinerary.offers
    )


def test_manual_promo_and_member_notes_are_attached_to_booking_options() -> None:
    response = search(request(
        promoCodeNote="Try code EOFY10",
        memberPriceNote="Check Trip.com member tier manually",
    ))
    notes = response.ranked_results[0].booking_options[0].notes
    assert "Promo code note: Try code EOFY10" in notes
    assert "Member price note: Check Trip.com member tier manually" in notes


def test_trip_com_affiliate_option_cannot_be_confirmed() -> None:
    with pytest.raises(ValidationError, match="Trip.com"):
        BookingOption(
            type=BookingOptionType.trip_com,
            label="Check on Trip.com",
            supplier=Supplier.trip_com_affiliate,
            url="https://example.invalid/tripcom-affiliate?tracking_id=SPLITFARE_PLACEHOLDER",
            priceAmount=100,
            currency="AUD",
            priceConfidence=PriceConfidence.confirmed,
        )
