import asyncio
import time
from datetime import date

from app.adapters.duffel import DuffelSupplierAdapter
from app.adapters.mock_supplier import MockSupplierAdapter
from app.adapters.orchestrator import SupplierOrchestrator
from app.adapters.trip_com import TripComAffiliateAdapter
from app.models import Cabin, SearchCacheContext, SearchRequest, SearchStatus, Supplier, SupplierCapabilities
from app.config import Settings
from app.search import SearchService
from app.search_orchestrator import (
    MAX_HUBS,
    SearchOrchestrator,
    generate_candidate_hubs,
    generate_query_plan,
)


def request(hubs: list[str] | None = None) -> SearchRequest:
    return SearchRequest(
        originCityId="city:melbourne-au", destinationCityId="city:shanghai-cn", departureDate=date(2026, 8, 12),
        minGapHours=3, maxGapHours=12, passengers=1, cabin="economy",
        candidateHubs=hubs,
    )


CONTEXT = SearchCacheContext(
    originCityId="city:melbourne-au", destinationCityId="city:shanghai-cn",
    resolvedOriginAirports=["MEL", "AVV"], resolvedDestinationAirports=["PVG", "SHA"],
    minGapHours=3, maxGapHours=12, supplierMode="mock",
)


class DelayedMockAdapter(MockSupplierAdapter):
    def __init__(self, *args, delay: float, **kwargs):
        super().__init__(*args, **kwargs)
        self.delay = delay

    def _fetch_one_way(self, *args, **kwargs):
        time.sleep(self.delay)
        return super()._fetch_one_way(*args, **kwargs)


class SecretFailureAdapter(DuffelSupplierAdapter):
    @property
    def capabilities(self):
        return SupplierCapabilities(supports_search=True)

    def _fetch_one_way(self, *args, **kwargs):
        raise RuntimeError(
            "api_key=super-secret token:also-secret Authorization=Bearer-secret Bearer abc.xyz"
        )


class BurstMockAdapter(MockSupplierAdapter):
    def normalize(self, raw_response):
        offers = super().normalize(raw_response)
        if not offers:
            return []
        return [offers[0].model_copy(update={"id": f"burst-{index}"}) for index in range(35)]


class RecordingDuffelAdapter(DuffelSupplierAdapter):
    def __init__(self):
        super().__init__(Settings(
            enable_mock_supplier=False,
            duffel_mode="sandbox",
            duffel_api_token="duffel_test_fixture",
        ))
        self.routes: list[tuple[str, str]] = []

    def _fetch_one_way(self, origin, destination, departure_date, passengers, cabin, currency):
        self.routes.append((origin, destination))
        return {"data": {"live_mode": False, "offers": []}, "_splitfare": {"mode": "sandbox", "cabin": cabin.value}}


def test_mel_to_pvg_generates_baseline_and_hub_query_plan() -> None:
    plan = generate_query_plan(request())
    assert plan[0].origin == "MEL" and plan[0].destination == "PVG"
    assert plan[0].kind == "baseline"
    assert len(generate_candidate_hubs(request())) == MAX_HUBS
    assert len(plan) == 4 + MAX_HUBS * 6
    assert any(item.origin == "MEL" and item.destination == "BKK" for item in plan)
    assert any(item.origin == "BKK" and item.destination == "PVG" for item in plan)


def test_custom_hubs_are_deduplicated_without_recursion() -> None:
    search_request = request(["BKK", "BKK", "SIN"])
    assert generate_candidate_hubs(search_request) == ("BKK", "SIN")
    assert len(generate_query_plan(search_request)) == 16


def test_real_adapter_receives_all_city_resolved_baseline_airport_pairs() -> None:
    adapter = RecordingDuffelAdapter()
    low_level = SupplierOrchestrator([adapter], supplier_mode="sandbox")
    asyncio.run(SearchOrchestrator(low_level, 1).collect_offers(request([])))
    assert set(adapter.routes) == {
        ("MEL", "PVG"), ("MEL", "SHA"), ("AVV", "PVG"), ("AVV", "SHA")
    }


def test_route_queries_run_concurrently() -> None:
    low_level = SupplierOrchestrator([
        DelayedMockAdapter(delay=0.15),
    ], supplier_timeout_seconds=1)
    orchestrator = SearchOrchestrator(low_level, total_timeout_seconds=2)
    started = time.perf_counter()
    asyncio.run(orchestrator.collect_offers(request(["BKK"])))
    elapsed = time.perf_counter() - started
    assert elapsed < 0.35  # Three 150ms route calls would take ~450ms sequentially.


def test_supplier_timeout_keeps_other_supplier_results() -> None:
    low_level = SupplierOrchestrator([
        DelayedMockAdapter(Supplier.demo_air, delay=0.15),
        MockSupplierAdapter(Supplier.mock_sky),
    ], supplier_timeout_seconds=0.02)
    outcome = asyncio.run(SearchOrchestrator(low_level, 1).collect_offers(request(["BKK"])))
    assert any(offer.supplier == Supplier.mock_sky for offer in outcome.offers)
    assert any(error.code == "SUPPLIER_TIMEOUT" for error in outcome.errors)


def test_total_timeout_cancels_pending_route_queries() -> None:
    low_level = SupplierOrchestrator([
        DelayedMockAdapter(delay=0.15),
    ], supplier_timeout_seconds=1)
    outcome = asyncio.run(
        SearchOrchestrator(low_level, total_timeout_seconds=0.02).collect_offers(request(["BKK"]))
    )
    assert outcome.offers == ()
    assert any(error.code == "SEARCH_TIMEOUT" for error in outcome.errors)


def test_supplier_leg_results_are_capped_at_30() -> None:
    low_level = SupplierOrchestrator(
        [BurstMockAdapter()], max_offers_per_supplier_leg=30
    )
    result = asyncio.run(low_level.search_route(
        "MEL", "PVG", date(2026, 8, 12), 1, Cabin.economy, "AUD", CONTEXT
    ))
    assert len(result.offers) == 30


def test_sensitive_values_are_redacted_from_errors() -> None:
    low_level = SupplierOrchestrator([SecretFailureAdapter()])
    outcome = asyncio.run(SearchOrchestrator(low_level, 1).collect_offers(request([])))
    message = outcome.errors[0].message
    assert "super-secret" not in message
    assert "also-secret" not in message
    assert "abc.xyz" not in message
    assert "[REDACTED]" in message


def test_no_results_returns_empty_response_instead_of_exception() -> None:
    low_level = SupplierOrchestrator([TripComAffiliateAdapter()])
    service = SearchService(SearchOrchestrator(low_level, 1))
    response = asyncio.run(service.search(request(["BKK"])))
    assert response.status == SearchStatus.empty
    assert response.results.ranked_results == []
    assert response.results.protected_itineraries == []
    assert response.results.split_ticket_itineraries == []
    assert response.explanation


def test_supplier_failure_yields_partial_search_response() -> None:
    low_level = SupplierOrchestrator([
        MockSupplierAdapter(Supplier.mock_sky), SecretFailureAdapter(),
    ])
    service = SearchService(SearchOrchestrator(low_level, 1))
    response = asyncio.run(service.search(request(["BKK"])))
    assert response.status == SearchStatus.partial
    assert response.results.ranked_results
    assert response.errors
    assert response.search_id


def test_all_real_supplier_failures_return_failed_not_empty_or_mock() -> None:
    adapter = DuffelSupplierAdapter(Settings(
        enable_mock_supplier=False,
        duffel_mode="sandbox",
        duffel_api_token=None,
    ))
    low_level = SupplierOrchestrator([adapter], supplier_mode="sandbox")
    response = asyncio.run(SearchService(SearchOrchestrator(low_level, 1)).search(request([])))
    assert response.status == SearchStatus.failed
    assert response.results.ranked_results == []
    assert response.metadata.mode == "sandbox"
    assert response.metadata.demo_data is False
    assert response.errors
    assert {error.code for error in response.errors} == {"SUPPLIER_AUTH_FAILED"}
