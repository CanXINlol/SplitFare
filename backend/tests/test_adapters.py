from datetime import date

import pytest

from app.adapters.base import (
    AdapterNotConfiguredError,
    UnsupportedSupplierCapabilityError,
)
from app.adapters.duffel import DuffelSupplierAdapter
from app.adapters.mock_supplier import MockSupplierAdapter
from app.adapters.orchestrator import SupplierOrchestrator
from app.adapters.skyscanner import SkyscannerSupplierAdapter
from app.adapters.trip_com import TripComAffiliateAdapter
from app.models import (
    Cabin,
    NormalizedFlightOffer,
    SearchRequest,
    Supplier,
    VerificationStatus,
)


DEPARTURE_DATE = date(2026, 8, 12)


def search_request() -> SearchRequest:
    return SearchRequest(
        origin="MEL", destination="PVG", departureDate=DEPARTURE_DATE,
        minGapHours=3, maxGapHours=12, passengers=1, cabin="economy",
    )


def one_way(adapter):
    return adapter.search_one_way(
        "MEL", "PVG", DEPARTURE_DATE, 1, Cabin.economy, "AUD"
    )


def test_mock_adapter_returns_normalized_offers_with_its_supplier() -> None:
    adapter = MockSupplierAdapter(Supplier.mock_sky)
    offers = one_way(adapter)
    assert offers
    assert all(isinstance(item, NormalizedFlightOffer) for item in offers)
    assert all(item.supplier == adapter.name for item in offers)


def test_base_search_always_calls_normalize_before_returning() -> None:
    class CountingMockAdapter(MockSupplierAdapter):
        normalize_calls = 0

        def normalize(self, raw_response):
            self.normalize_calls += 1
            return super().normalize(raw_response)

    adapter = CountingMockAdapter()
    one_way(adapter)
    assert adapter.normalize_calls == 1


def test_mock_price_verification_is_deterministic() -> None:
    result = MockSupplierAdapter().verify_price("offer-direct-mu")
    assert result.status == VerificationStatus.verified
    assert result.price_amount == 1120
    assert result.currency == "AUD"


def test_optional_multi_city_defaults_to_unsupported() -> None:
    with pytest.raises(UnsupportedSupplierCapabilityError):
        MockSupplierAdapter().search_multi_city([], 1, Cabin.economy, "AUD")


@pytest.mark.parametrize(
    "adapter_type",
    [DuffelSupplierAdapter, SkyscannerSupplierAdapter],
)
def test_external_supplier_skeletons_are_not_configured(adapter_type) -> None:
    adapter = adapter_type()
    with pytest.raises(AdapterNotConfiguredError):
        one_way(adapter)
    assert adapter.verify_price("future-offer").status == VerificationStatus.not_configured


def test_trip_com_adapter_only_builds_placeholder_deep_link() -> None:
    adapter = TripComAffiliateAdapter()
    link = adapter.build_deep_link(
        "MEL", "PVG", DEPARTURE_DATE, 1, Cabin.economy, "AUD"
    )
    assert link.startswith("https://example.invalid/tripcom-affiliate?")
    assert "SPLITFARE_PLACEHOLDER" in link
    assert one_way(adapter) == []


def test_trip_com_cannot_verify_prices() -> None:
    result = TripComAffiliateAdapter().verify_price("affiliate-link")
    assert result.status == VerificationStatus.unavailable
    assert result.price_amount is None


def test_orchestrator_combines_multiple_mock_suppliers() -> None:
    orchestrator = SupplierOrchestrator([
        MockSupplierAdapter(Supplier.mock_sky),
        MockSupplierAdapter(Supplier.demo_air),
        MockSupplierAdapter(Supplier.budget_demo),
    ])
    outcome = orchestrator.search(search_request())
    assert {offer.supplier for offer in outcome.offers} == {
        Supplier.mock_sky, Supplier.demo_air,
    }
    assert outcome.failures == []


def test_one_supplier_failure_does_not_discard_other_results() -> None:
    orchestrator = SupplierOrchestrator([
        DuffelSupplierAdapter(),
        MockSupplierAdapter(Supplier.mock_sky),
        SkyscannerSupplierAdapter(),
    ])
    outcome = orchestrator.search(search_request())
    assert outcome.offers
    assert {failure.supplier for failure in outcome.failures} == {
        Supplier.duffel, Supplier.skyscanner,
    }


def test_orchestrator_rejects_supplier_mismatch_without_breaking_others() -> None:
    class MismatchedMockAdapter(MockSupplierAdapter):
        def normalize(self, raw_response):
            offers = super().normalize(raw_response)
            return [offer.model_copy(update={"supplier": Supplier.duffel}) for offer in offers]

    outcome = SupplierOrchestrator([
        MismatchedMockAdapter(), MockSupplierAdapter(Supplier.demo_air)
    ]).search(search_request())
    assert all(offer.supplier == Supplier.demo_air for offer in outcome.offers)
    assert outcome.failures[0].supplier == Supplier.mock_sky


def test_orchestrator_deduplicates_same_supplier_offer_ids() -> None:
    adapter = MockSupplierAdapter(Supplier.mock_sky)
    outcome = SupplierOrchestrator([adapter, adapter]).search(search_request())
    keys = {(offer.supplier, offer.id) for offer in outcome.offers}
    assert len(keys) == len(outcome.offers)
