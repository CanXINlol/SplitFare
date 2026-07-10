import asyncio
from datetime import date, datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app.adapters.mock_supplier import build_mock_orchestrator
from app.adapters.trip_com import TRIP_COM_TRACKING_ID, TripComAffiliateAdapter
from app.models import (
    BookingOption,
    BookingOptionType,
    PriceStatus,
    SearchRequest,
    Supplier,
)
from app.search import SearchService
from app.search_orchestrator import SearchOrchestrator


def request(**updates) -> SearchRequest:
    data = {
        "originCityId": "city:melbourne-au",
        "destinationCityId": "city:shanghai-cn",
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
        for itinerary in response.results.ranked_results
        for option in itinerary.booking_options
        if option.type == BookingOptionType.trip_com
    ]
    assert trip_options
    assert all(option.label == "Check on Trip.com" for option in trip_options)
    assert all(option.tracking_id == TRIP_COM_TRACKING_ID for option in trip_options)
    assert all(option.price_status == PriceStatus.redirect_only for option in trip_options)
    assert all(option.price_amount is None for option in trip_options)
    assert all("tracking_id=splitfare_demo" in str(option.url) for option in trip_options)


def test_skyscanner_booking_option_is_redirect_only() -> None:
    response = search(request())
    options = [
        option
        for itinerary in response.results.ranked_results
        for option in itinerary.booking_options
        if option.type == BookingOptionType.skyscanner
    ]
    assert options
    assert all(option.price_status == PriceStatus.redirect_only for option in options)
    assert all(option.price_amount is None for option in options)
    assert all(not option.verification_required for option in options)


def test_mock_supplier_booking_option_has_confirmed_price_status() -> None:
    response = search(request())
    supplier_options = [
        option
        for itinerary in response.results.ranked_results
        for option in itinerary.booking_options
        if option.type == BookingOptionType.supplier
    ]
    assert supplier_options
    assert all(option.price_status == PriceStatus.confirmed for option in supplier_options)
    assert all(option.price_amount is not None for option in supplier_options)


def test_split_ticket_booking_options_are_bound_per_ticket_and_sum_to_total() -> None:
    response = search(request())
    itinerary = response.results.split_ticket_itineraries[0]
    supplier_options = [
        option for option in itinerary.booking_options
        if option.type == BookingOptionType.supplier
    ]
    assert len(supplier_options) == len(itinerary.offers) == 2
    assert sum(option.price_amount for option in supplier_options if option.price_amount) == itinerary.total_price
    assert {option.offer_id for option in supplier_options} == {offer.id for offer in itinerary.offers}


def test_trip_com_deep_link_does_not_create_fare_offers_or_affect_sorting() -> None:
    response = search(request(sort="cheapest"))
    cheapest_before_options = response.results.ranked_results[0].total_price
    assert TripComAffiliateAdapter().search_one_way(
        "MEL", "PVG", date(2026, 8, 12), 1, request().cabin, "AUD"
    ) == []
    assert response.results.ranked_results[0].total_price == cheapest_before_options
    assert all(
        offer.supplier != Supplier.trip_com_affiliate
        for itinerary in response.results.ranked_results
        for offer in itinerary.offers
    )


def test_manual_promo_and_member_notes_are_attached_to_booking_options() -> None:
    response = search(request(
        promoCodeNote="Try code EOFY10",
        memberPriceNote="Check Trip.com member tier manually",
    ))
    notes = response.results.ranked_results[0].booking_options[0].notes
    assert "Promo code note: Try code EOFY10" in notes
    assert "Member price note: Check Trip.com member tier manually" in notes


def test_trip_com_affiliate_option_cannot_be_confirmed() -> None:
    with pytest.raises(ValidationError, match="Trip.com"):
        BookingOption(
            id="trip-com-test",
            type=BookingOptionType.trip_com,
            label="Check on Trip.com",
            supplier=Supplier.trip_com_affiliate,
            url="https://www.trip.com/flights/?tracking_id=splitfare_demo",
            priceAmount=100,
            currency="AUD",
            priceStatus=PriceStatus.confirmed,
        )


def test_unsafe_booking_url_protocol_is_rejected() -> None:
    with pytest.raises(ValidationError):
        BookingOption(
            id="unsafe", type=BookingOptionType.supplier, label="Unsafe",
            supplier=Supplier.mock_sky, url="javascript:alert(1)",
            priceAmount=100, currency="AUD",
            priceStatus=PriceStatus.confirmed,
            capabilities={"supportsPriceVerify": False},
        )


def test_production_safe_booking_options_do_not_use_example_hosts() -> None:
    response = search(request())
    serialized = response.model_dump_json(by_alias=True)
    assert "example.com" not in serialized
    assert "example.invalid" not in serialized


def test_expired_confirmed_booking_option_is_downgraded_to_cached() -> None:
    checked = datetime.now(timezone.utc) - timedelta(minutes=10)
    option = BookingOption(
        id="expired", type=BookingOptionType.supplier, label="Expired demo price",
        supplier=Supplier.mock_sky, offerId="offer-expired",
        capabilities={"supportsPriceVerify": True},
        priceAmount=100, currency="AUD",
        priceStatus=PriceStatus.confirmed, lastCheckedAt=checked,
        expiresAt=checked + timedelta(minutes=5),
    )
    assert option.price_status == PriceStatus.cached
