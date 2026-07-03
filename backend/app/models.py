from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator


def to_camel(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part.title() for part in tail)


class ApiModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")


class Supplier(str, Enum):
    mock_sky = "MockSky"
    demo_air = "DemoAir"
    budget_demo = "BudgetDemo"
    duffel = "Duffel"
    skyscanner = "Skyscanner"
    trip_com_affiliate = "TripComAffiliate"


class ItineraryType(str, Enum):
    protected = "protected"
    split_ticket = "split_ticket"


class RiskLevel(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    extreme = "extreme"


class Cabin(str, Enum):
    economy = "economy"
    premium_economy = "premium_economy"
    business = "business"
    first = "first"


class SortOption(str, Enum):
    value = "value"
    cheapest = "cheapest"


class VerificationStatus(str, Enum):
    verified = "verified"
    expired = "expired"
    unavailable = "unavailable"
    not_configured = "not_configured"


class BookingOptionType(str, Enum):
    airline = "airline"
    trip_com = "trip_com"
    skyscanner = "skyscanner"
    supplier = "supplier"


class PriceConfidence(str, Enum):
    confirmed = "confirmed"
    check_required = "check_required"
    unavailable = "unavailable"


class SearchStatus(str, Enum):
    complete = "complete"
    partial = "partial"
    empty = "empty"


class SearchRequest(ApiModel):
    origin: str = Field(pattern=r"^[A-Z]{3}$")
    destination: str = Field(pattern=r"^[A-Z]{3}$")
    departure_date: date
    min_gap_hours: float = Field(ge=1, le=24)
    max_gap_hours: float = Field(ge=1, le=36)
    passengers: int = Field(ge=1, le=9)
    cabin: Cabin = Cabin.economy
    max_results: int = Field(default=20, ge=1, le=100)
    sort: SortOption = SortOption.value
    checked_baggage_likely_required: bool = False
    visa_transit_requirement_unknown: bool = True
    currency: str = Field(default="AUD", pattern=r"^[A-Z]{3}$")
    candidate_hubs: list[str] | None = Field(default=None, max_length=12)
    promo_code_note: str | None = Field(default=None, max_length=240)
    member_price_note: str | None = Field(default=None, max_length=240)

    @field_validator("origin", "destination", "currency", mode="before")
    @classmethod
    def normalize_iata(cls, value: object) -> object:
        return value.strip().upper() if isinstance(value, str) else value

    @field_validator("candidate_hubs", mode="before")
    @classmethod
    def normalize_hubs(cls, value: object) -> object:
        if isinstance(value, list):
            return [item.strip().upper() if isinstance(item, str) else item for item in value]
        return value

    @model_validator(mode="after")
    def validate_search(self) -> SearchRequest:
        if self.origin == self.destination:
            raise ValueError("origin and destination must differ")
        if self.max_gap_hours < self.min_gap_hours:
            raise ValueError("max_gap_hours must be greater than or equal to min_gap_hours")
        if self.candidate_hubs:
            if any(len(hub) != 3 or not hub.isalpha() for hub in self.candidate_hubs):
                raise ValueError("candidate hubs must be three-letter IATA codes")
            if self.origin in self.candidate_hubs or self.destination in self.candidate_hubs:
                raise ValueError("candidate hubs cannot equal origin or destination")
        return self


class Segment(ApiModel):
    id: str = Field(min_length=1)
    origin: str = Field(pattern=r"^[A-Z]{3}$")
    destination: str = Field(pattern=r"^[A-Z]{3}$")
    departure_at: datetime
    arrival_at: datetime
    airline: str = Field(min_length=2)
    operating_airline: str = Field(min_length=2)
    flight_number: str = Field(min_length=3)

    @field_validator("departure_at", "arrival_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("flight times must include a timezone")
        return value

    @model_validator(mode="after")
    def validate_route_and_time(self) -> Segment:
        if self.origin == self.destination:
            raise ValueError("segment origin and destination must differ")
        if self.arrival_at <= self.departure_at:
            raise ValueError("arrival_at must be later than departure_at")
        return self


class FlightSlice(ApiModel):
    origin: str = Field(pattern=r"^[A-Z]{3}$")
    destination: str = Field(pattern=r"^[A-Z]{3}$")
    departure_date: date


class PriceVerification(ApiModel):
    offer_id: str
    supplier: Supplier
    status: VerificationStatus
    price_amount: float | None = Field(default=None, gt=0)
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    checked_at: datetime
    expires_at: datetime | None = None
    is_confirmed: bool = False
    message: str

    @field_validator("checked_at", "expires_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("verification times must include a timezone")
        return value

    @model_validator(mode="after")
    def validate_confirmation_status(self) -> PriceVerification:
        if self.expires_at is not None and self.expires_at <= self.checked_at:
            raise ValueError("expires_at must be later than checked_at")
        is_confirmed = (
            self.status == VerificationStatus.verified
            and self.price_amount is not None
            and self.currency is not None
            and self.expires_at is not None
            and self.expires_at > datetime.now(self.expires_at.tzinfo)
        )
        object.__setattr__(self, "is_confirmed", is_confirmed)
        return self


class PreBookingVerificationRequest(ApiModel):
    search_id: str | None = None
    itinerary_id: str = Field(min_length=1)
    offer_id: str | None = None
    supplier: Supplier
    booking_option_type: BookingOptionType
    booking_option_label: str = Field(min_length=1)
    previous_price: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    booking_url: HttpUrl | None = None
    tracking_id: str | None = None


class PreBookingVerificationResponse(ApiModel):
    still_available: bool
    current_price: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    previous_price: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    price_changed: bool
    booking_url: HttpUrl | None = None
    checked_at: datetime
    expires_at: datetime | None = None
    status: VerificationStatus
    message: str
    can_continue: bool = False
    requires_price_check: bool = False

    @field_validator("checked_at", "expires_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("pre-booking verification times must include a timezone")
        return value


class SupplierFailure(ApiModel):
    supplier: Supplier
    error_type: str
    message: str


class FlightQuery(ApiModel):
    origin: str = Field(pattern=r"^[A-Z]{3}$")
    destination: str = Field(pattern=r"^[A-Z]{3}$")
    departure_date: date
    kind: str
    hub: str | None = None


class SearchError(ApiModel):
    supplier: Supplier | None
    origin: str | None
    destination: str | None
    code: str
    message: str


class PriceFreshness(ApiModel):
    last_checked_at: datetime
    expires_at: datetime
    is_expired: bool

    @field_validator("last_checked_at", "expires_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("price freshness times must include a timezone")
        return value

    @model_validator(mode="after")
    def validate_times(self) -> PriceFreshness:
        if self.expires_at <= self.last_checked_at:
            raise ValueError("expires_at must be later than last_checked_at")
        return self


class BookingOption(ApiModel):
    type: BookingOptionType
    label: str = Field(min_length=1)
    supplier: Supplier | None = None
    url: HttpUrl | None = None
    price_amount: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    price_confidence: PriceConfidence
    tracking_id: str | None = None
    last_checked_at: datetime | None = None
    expires_at: datetime | None = None
    notes: list[str] = Field(default_factory=list)

    @field_validator("last_checked_at", "expires_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("booking option times must include a timezone")
        return value

    @model_validator(mode="after")
    def validate_price_confidence(self) -> BookingOption:
        if self.type == BookingOptionType.trip_com and self.price_confidence == PriceConfidence.confirmed:
            raise ValueError("Trip.com affiliate/deep-link prices cannot be marked confirmed.")
        if self.price_confidence == PriceConfidence.confirmed and (
            self.price_amount is None or self.currency is None
        ):
            raise ValueError("confirmed booking options require price and currency")
        return self


class PriceSourceCoverage(ApiModel):
    confirmed_supplier_count: int = Field(ge=0)
    check_required_supplier_count: int = Field(ge=0)
    unavailable_supplier_count: int = Field(ge=0)
    labels: list[str] = Field(default_factory=list)


class NormalizedFlightOffer(ApiModel):
    id: str = Field(min_length=1)
    supplier: Supplier
    origin: str = Field(pattern=r"^[A-Z]{3}$")
    destination: str = Field(pattern=r"^[A-Z]{3}$")
    departure_at: datetime
    arrival_at: datetime
    airline: str = Field(min_length=2)
    operating_airline: str = Field(min_length=2)
    flight_number: str = Field(min_length=3)
    price_amount: float = Field(gt=0, allow_inf_nan=False)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    cabin: Cabin
    baggage_included: bool | None
    booking_url: HttpUrl | None = None
    raw_payload: dict[str, Any] = Field(default_factory=dict)
    last_checked_at: datetime
    expires_at: datetime
    segments: list[Segment] = Field(min_length=1)
    protected_connection: bool = False

    @field_validator("departure_at", "arrival_at", "last_checked_at", "expires_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("offer times must include a timezone")
        return value

    @model_validator(mode="after")
    def validate_normalized_offer(self) -> NormalizedFlightOffer:
        first, last = self.segments[0], self.segments[-1]
        if (self.origin, self.destination) != (first.origin, last.destination):
            raise ValueError("offer endpoints must match its first and last segments")
        if (self.departure_at, self.arrival_at) != (first.departure_at, last.arrival_at):
            raise ValueError("offer times must match its first and last segments")
        if self.arrival_at <= self.departure_at:
            raise ValueError("arrival_at must be later than departure_at")
        if self.expires_at <= self.last_checked_at:
            raise ValueError("expires_at must be later than last_checked_at")
        for previous, current in zip(self.segments, self.segments[1:]):
            if previous.destination != current.origin or previous.arrival_at >= current.departure_at:
                raise ValueError("offer segments must form a chronological route")
        return self


class PriceSnapshot(ApiModel):
    id: str = Field(min_length=1)
    search_id: str = Field(min_length=1)
    offer_id: str = Field(min_length=1)
    supplier: Supplier
    origin: str = Field(pattern=r"^[A-Z]{3}$")
    destination: str = Field(pattern=r"^[A-Z]{3}$")
    departure_date: date
    passengers: int = Field(ge=1, le=9)
    cabin: Cabin
    price_amount: float = Field(gt=0, allow_inf_nan=False)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    last_checked_at: datetime
    expires_at: datetime
    verification_status: VerificationStatus
    cache_key: str | None = None
    created_at: datetime

    @field_validator("last_checked_at", "expires_at", "created_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("snapshot times must include a timezone")
        return value

    @model_validator(mode="after")
    def validate_snapshot(self) -> PriceSnapshot:
        if self.origin == self.destination:
            raise ValueError("snapshot origin and destination must differ")
        if self.expires_at <= self.last_checked_at:
            raise ValueError("expires_at must be later than last_checked_at")
        if self.verification_status == VerificationStatus.verified and self.expires_at <= self.created_at:
            raise ValueError("expired prices cannot be recorded as verified")
        return self


class SupplierSearchOutcome(ApiModel):
    offers: list[NormalizedFlightOffer]
    failures: list[SupplierFailure]


class RiskAssessment(ApiModel):
    score: int = Field(ge=0, le=100)
    level: RiskLevel
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_level_matches_score(self) -> RiskAssessment:
        expected = (RiskLevel.low if self.score <= 25 else RiskLevel.medium if self.score <= 55
                    else RiskLevel.high if self.score <= 80 else RiskLevel.extreme)
        if self.level != expected:
            raise ValueError(f"risk level {self.level} does not match score {self.score}")
        return self


class Itinerary(ApiModel):
    id: str = Field(min_length=1)
    type: ItineraryType
    total_price: float = Field(gt=0, allow_inf_nan=False)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    total_duration_minutes: int = Field(gt=0)
    layover_airport: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    layover_gap_minutes: int | None = Field(default=None, ge=0)
    risk_score: int = Field(ge=0, le=100)
    risk_level: RiskLevel
    savings_vs_baseline: float | None = Field(default=None, allow_inf_nan=False)
    value_score: float = Field(ge=0, le=100)
    warnings: list[str]
    segments: list[Segment] = Field(min_length=1)
    offers: list[NormalizedFlightOffer] = Field(min_length=1)
    risk_assessment: RiskAssessment
    suppliers: list[Supplier] = Field(min_length=1)
    last_checked_at: datetime
    expires_at: datetime
    price_freshness: PriceFreshness
    booking_options: list[BookingOption] = Field(default_factory=list)
    price_source_coverage: PriceSourceCoverage | None = None
    layover_departure_airport: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    requires_ground_transfer: bool = False

    @model_validator(mode="after")
    def validate_itinerary(self) -> Itinerary:
        if any(offer.currency != self.currency for offer in self.offers):
            raise ValueError("all itinerary offers must use the itinerary currency")
        flattened = [segment.id for offer in self.offers for segment in offer.segments]
        if flattened != [segment.id for segment in self.segments]:
            raise ValueError("itinerary segments must be the ordered flattened offer segments")
        if (self.risk_score, self.risk_level, self.warnings) != (
            self.risk_assessment.score, self.risk_assessment.level, self.risk_assessment.warnings
        ):
            raise ValueError("top-level risk fields must match risk_assessment")
        if (self.layover_airport is None) != (self.layover_gap_minutes is None):
            raise ValueError("layover airport and gap must either both be set or both be null")
        if self.requires_ground_transfer and self.layover_departure_airport is None:
            raise ValueError("ground transfer requires a layover departure airport")
        if (
            self.price_freshness.last_checked_at,
            self.price_freshness.expires_at,
        ) != (self.last_checked_at, self.expires_at):
            raise ValueError("price freshness must match itinerary price timestamps")
        return self


class MatchingRequest(ApiModel):
    origin: str = Field(pattern=r"^[A-Z]{3}$")
    destination: str = Field(pattern=r"^[A-Z]{3}$")
    departure_date: date
    min_gap_minutes: int = Field(ge=0)
    max_gap_minutes: int = Field(gt=0)
    max_results: int = Field(ge=1, le=100)
    offers: tuple[NormalizedFlightOffer, ...]
    sort: SortOption = SortOption.value
    checked_baggage_likely_required: bool = False
    visa_transit_requirement_unknown: bool = True

    @model_validator(mode="after")
    def validate_matching_request(self) -> MatchingRequest:
        if self.origin == self.destination:
            raise ValueError("origin and destination must differ")
        if self.max_gap_minutes < self.min_gap_minutes:
            raise ValueError("max_gap_minutes must be greater than or equal to min_gap_minutes")
        return self


class MatchingResult(ApiModel):
    protected_itineraries: list[Itinerary]
    split_ticket_itineraries: list[Itinerary]
    baseline_price: float | None
    ranked_results: list[Itinerary]


class SearchResults(ApiModel):
    protected_itineraries: list[Itinerary]
    split_ticket_itineraries: list[Itinerary]
    baseline_price: float | None
    ranked_results: list[Itinerary]


class SearchResponse(ApiModel):
    search_id: str
    status: SearchStatus
    results: SearchResults
    errors: list[SearchError]
    explanation: str
    baseline: Itinerary | None
    cheapest_split: Itinerary | None
    safest_split: Itinerary | None
    ranked: list[Itinerary]
    protected_itineraries: list[Itinerary]
    split_ticket_itineraries: list[Itinerary]
    baseline_price: float | None
    ranked_results: list[Itinerary]
    supplier_failures: list[SupplierFailure] = Field(default_factory=list)
    disclaimer: str = Field(min_length=1)
