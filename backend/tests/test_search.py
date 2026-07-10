import asyncio
from datetime import date

from app.adapters.mock_supplier import build_mock_orchestrator
from app.models import SearchRequest
from app.risk import SELF_TRANSFER_WARNING
from app.search import SearchService
from app.search_orchestrator import SearchOrchestrator


def request(min_gap: float = 3, max_gap: float = 12) -> SearchRequest:
    return SearchRequest(
        originPlaceId="airport:MEL", destinationPlaceId="airport:PVG", departureDate=date(2026, 8, 12),
        minGapHours=min_gap, maxGapHours=max_gap, passengers=1, cabin="economy",
    )


def search(search_request: SearchRequest):
    service = SearchService(SearchOrchestrator(build_mock_orchestrator()))
    return asyncio.run(service.search(search_request))


def test_returns_baseline_and_at_least_five_ranked_results() -> None:
    result = search(request())
    assert result.baseline.type == "protected"
    assert len(result.results.ranked_results) >= 5
    assert sum(item.type == "split_ticket" for item in result.results.ranked_results) >= 2


def test_split_results_obey_gap_and_show_warning() -> None:
    result = search(request(4, 8))
    splits = [item for item in result.results.ranked_results if item.type == "split_ticket"]
    assert splits
    assert all(240 <= (item.layover_gap_minutes or 0) <= 480 for item in splits)
    assert all(item.risk_level.value != "low" for item in splits)
    assert all(SELF_TRANSFER_WARNING in item.warnings for item in splits)


def test_passenger_count_scales_total_price() -> None:
    one = search(request()).baseline.total_price
    multi = request()
    multi.passengers = 2
    two = search(multi).baseline.total_price
    assert two == one * 2
