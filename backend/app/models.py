from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_serializer, field_validator, model_validator


def to_camel(value: str) -> str:
    head, *tail = value.split("_")
    return head + "".join(part.title() for part in tail)


class ApiModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, extra="forbid")

    @field_serializer("*", when_used="json", check_fields=False)
    def serialize_decimal_fields(self, value: object) -> object:
        return float(value) if isinstance(value, Decimal) else value


def validate_booking_url(value: HttpUrl | None) -> HttpUrl | None:
    if value is None:
        return None
    if value.username or value.password:
        raise ValueError("booking URLs cannot contain credentials")
    if value.scheme == "http" and value.host not in {"localhost", "127.0.0.1", "::1"}:
        raise ValueError("external booking URLs must use HTTPS")
    return value


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


def risk_level_for_score(score: int) -> RiskLevel:
    if score <= 25:
        return RiskLevel.low
    if score <= 55:
        return RiskLevel.medium
    if score <= 80:
        return RiskLevel.high
    return RiskLevel.extreme


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
    unsupported = "unsupported"
    timeout = "timeout"


class BookingOptionType(str, Enum):
    airline = "airline"
    trip_com = "trip_com"
    skyscanner = "skyscanner"
    supplier = "supplier"


class PriceStatus(str, Enum):
    confirmed = "confirmed"
    cached = "cached"
    estimated = "estimated"
    redirect_only = "redirect_only"
    unavailable = "unavailable"


class SearchStatus(str, Enum):
    complete = "complete"
    partial = "partial"
    empty = "empty"


class CandidateAirport(ApiModel):
    iata_code: str = Field(pattern=r"^[A-Z]{3}$")
    name: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    city: str = Field(min_length=1)
    country: str = Field(min_length=1)
    is_primary: bool = False
    international: bool = True
    priority: int = Field(ge=1)
    distance_to_city_km: float = Field(default=0, ge=0)
    has_mock_flight_data: bool = False


class Continent(ApiModel):
    continent_id: str = Field(pattern=r"^[a-z-]+$")
    continent_name_zh: str = Field(min_length=1)
    continent_name_en: str = Field(min_length=1)
    priority: int = Field(ge=1)


class Country(ApiModel):
    country_id: str = Field(pattern=r"^[a-z-]+$")
    continent_id: str = Field(pattern=r"^[a-z-]+$")
    country_name_zh: str = Field(min_length=1)
    country_name_en: str = Field(min_length=1)
    country_code: str = Field(pattern=r"^[A-Z]{2}$")
    priority: int = Field(ge=1)


class City(ApiModel):
    city_id: str = Field(pattern=r"^city:[a-z0-9-]+$")
    city_name_zh: str = Field(min_length=1)
    city_name_en: str = Field(min_length=1)
    country_id: str = Field(pattern=r"^[a-z-]+$")
    airport_codes: list[str] = Field(min_length=1)
    priority: int = Field(ge=1)
    enabled: bool = True

    @field_validator("airport_codes")
    @classmethod
    def validate_airport_codes(cls, value: list[str]) -> list[str]:
        if any(len(code) != 3 or not code.isalpha() or code != code.upper() for code in value):
            raise ValueError("airport_codes must contain uppercase three-letter IATA codes")
        if len(value) != len(set(value)):
            raise ValueError("airport_codes must be unique within a city")
        return value


class CityCatalog(ApiModel):
    version: str = Field(min_length=1)
    continents: list[Continent]
    countries: list[Country]
    cities: list[City]


class ResolvedCity(ApiModel):
    city_id: str
    city_name_zh: str
    city_name_en: str
    country_id: str
    airports: list[CandidateAirport] = Field(min_length=1)


class SearchRequest(ApiModel):
    origin_city_id: str = Field(pattern=r"^city:[a-z0-9-]+$")
    destination_city_id: str = Field(pattern=r"^city:[a-z0-9-]+$")
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

    @field_validator("currency", mode="before")
    @classmethod
    def normalize_currency(cls, value: object) -> object:
        return value.strip().upper() if isinstance(value, str) else value

    @field_validator("origin_city_id", "destination_city_id", mode="before")
    @classmethod
    def normalize_city_id(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        return value.strip().lower()

    @field_validator("candidate_hubs", mode="before")
    @classmethod
    def normalize_hubs(cls, value: object) -> object:
        if isinstance(value, list):
            return [item.strip().upper() if isinstance(item, str) else item for item in value]
        return value

    @model_validator(mode="after")
    def validate_search(self) -> SearchRequest:
        if self.origin_city_id == self.destination_city_id:
            raise ValueError("origin and destination cities must differ")
        if self.max_gap_hours < self.min_gap_hours:
            raise ValueError("max_gap_hours must be greater than or equal to min_gap_hours")
        if self.candidate_hubs:
            if any(len(hub) != 3 or not hub.isalpha() for hub in self.candidate_hubs):
                raise ValueError("candidate hubs must be three-letter IATA codes")
        return self


class Segment(ApiModel):
    id: str = Field(min_length=1)
    origin: str = Field(pattern=r"^[A-Z]{3}$")
    destination: str = Field(pattern=r"^[A-Z]{3}$")
    origin_display: str | None = None
    destination_display: str | None = None
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
    price_status: PriceStatus = PriceStatus.unavailable
    price_amount: Decimal | None = Field(default=None, gt=0)
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    checked_at: datetime
    expires_at: datetime | None = None
    is_confirmed: bool = False
    supported: bool = True
    booking_url: HttpUrl | None = None
    message: str

    @model_validator(mode="before")
    @classmethod
    def infer_price_status(cls, value: object) -> object:
        if not isinstance(value, dict) or "price_status" in value or "priceStatus" in value:
            return value
        data = dict(value)
        status = data.get("status")
        if status == VerificationStatus.verified or status == VerificationStatus.verified.value:
            data["priceStatus"] = PriceStatus.confirmed
        elif status == VerificationStatus.expired or status == VerificationStatus.expired.value:
            data["priceStatus"] = PriceStatus.cached
        else:
            data["priceStatus"] = PriceStatus.unavailable
        return data

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
            and self.price_status == PriceStatus.confirmed
            and self.price_amount is not None
            and self.currency is not None
            and self.expires_at is not None
            and self.expires_at > datetime.now(self.expires_at.tzinfo)
        )
        object.__setattr__(self, "is_confirmed", is_confirmed)
        return self


class VerifyPriceResult(PriceVerification):
    pass


class PreBookingVerificationRequest(ApiModel):
    search_id: str = Field(min_length=1, max_length=80)
    itinerary_id: str = Field(min_length=1)
    booking_option_id: str = Field(min_length=1, max_length=500)


class PreBookingVerificationResponse(ApiModel):
    still_available: bool
    current_price: Decimal | None = Field(default=None, gt=0, allow_inf_nan=False)
    previous_price: Decimal | None = Field(default=None, gt=0, allow_inf_nan=False)
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


class SupplierCapabilities(ApiModel):
    supports_search: bool = False
    supports_price_verify: bool = False
    supports_booking_url: bool = False
    supports_baggage_info: bool = False
    supports_split_ticket: bool = False
    supports_live_price: bool = False
    supports_affiliate_link: bool = False


class SupplierError(ApiModel):
    supplier: Supplier
    code: str
    message: str
    retryable: bool = False


class SupplierResult(ApiModel):
    supplier: Supplier
    offers: list["NormalizedFlightOffer"] = Field(default_factory=list)
    errors: list[SupplierError] = Field(default_factory=list)
    capabilities: SupplierCapabilities
    fetched_at: datetime

    @field_validator("fetched_at")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("supplier result fetched_at must include a timezone")
        return value


class FlightQuery(ApiModel):
    origin: str = Field(pattern=r"^[A-Z]{3}$")
    destination: str = Field(pattern=r"^[A-Z]{3}$")
    departure_date: date
    kind: str
    hub: str | None = None


class SearchCacheContext(ApiModel):
    origin_city_id: str
    destination_city_id: str
    resolved_origin_airports: list[str]
    resolved_destination_airports: list[str]
    min_gap_hours: float
    max_gap_hours: float
    supplier_mode: str = Field(pattern=r"^(mock|live)$")


class AirportSearchMatrix(ApiModel):
    origin: ResolvedCity
    destination: ResolvedCity
    origin_airports: list[CandidateAirport] = Field(min_length=1, max_length=3)
    destination_airports: list[CandidateAirport] = Field(min_length=1, max_length=3)
    hubs: list[CandidateAirport] = Field(default_factory=list, max_length=12)
    excluded_hubs: list[str] = Field(default_factory=list)
    baseline_pairs: list[FlightQuery]
    query_plan: list[FlightQuery]
    query_plan_truncated: bool = False
    max_route_queries: int = Field(ge=1)


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


class SearchMetadata(ApiModel):
    mode: str = Field(pattern=r"^(mock|live)$")
    demo_data: bool
    searched_origin_airports: list[str]
    searched_destination_airports: list[str]
    searched_hubs: list[str]
    excluded_airports: list[str] = Field(default_factory=list)
    supplier_errors: list[SearchError] = Field(default_factory=list)
    route_query_count: int = Field(ge=0)
    supplier_query_count: int = Field(ge=0)
    supplier_query_limit: int = Field(ge=1)
    query_plan_truncated: bool = False
    fresh_price_count: int = Field(ge=0)
    expired_price_count: int = Field(ge=0)


class BookingOption(ApiModel):
    id: str = Field(min_length=1)
    type: BookingOptionType
    label: str = Field(min_length=1)
    display_name: str | None = None
    supplier: Supplier | None = None
    offer_id: str | None = None
    capabilities: SupplierCapabilities = Field(default_factory=SupplierCapabilities)
    url: HttpUrl | None = None
    booking_url: HttpUrl | None = None
    price_amount: Decimal | None = Field(default=None, gt=0, allow_inf_nan=False)
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    price_status: PriceStatus = PriceStatus.unavailable
    verification_required: bool = True
    tracking_id: str | None = None
    last_checked_at: datetime | None = None
    expires_at: datetime | None = None
    notes: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @field_validator("url", "booking_url")
    @classmethod
    def require_safe_url(cls, value: HttpUrl | None) -> HttpUrl | None:
        return validate_booking_url(value)

    @model_validator(mode="before")
    @classmethod
    def sync_legacy_and_final_fields(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        data = dict(value)
        if "display_name" not in data and "displayName" not in data and "label" in data:
            data["displayName"] = data["label"]
        if "booking_url" not in data and "bookingUrl" not in data and "url" in data:
            data["bookingUrl"] = data["url"]
        if "url" not in data and "bookingUrl" in data:
            data["url"] = data["bookingUrl"]
        return data

    @field_validator("last_checked_at", "expires_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("booking option times must include a timezone")
        return value

    @model_validator(mode="after")
    def validate_price_status(self) -> BookingOption:
        if self.url is None and self.booking_url is not None:
            object.__setattr__(self, "url", self.booking_url)
        if self.booking_url is None and self.url is not None:
            object.__setattr__(self, "booking_url", self.url)
        if self.display_name is None:
            object.__setattr__(self, "display_name", self.label)
        if self.type == BookingOptionType.trip_com and (
            self.price_status == PriceStatus.confirmed
        ):
            raise ValueError("Trip.com affiliate/deep-link prices cannot be marked confirmed.")
        if self.price_status == PriceStatus.redirect_only and self.price_amount is not None:
            raise ValueError("redirect-only booking options cannot include a confirmed price amount")
        if self.price_status == PriceStatus.confirmed and (
            self.price_amount is None or self.currency is None
        ):
            raise ValueError("confirmed booking options require price and currency")
        if (
            self.price_status == PriceStatus.confirmed
            and self.expires_at is not None
            and self.expires_at <= datetime.now(self.expires_at.tzinfo)
        ):
            object.__setattr__(self, "price_status", PriceStatus.cached)
        if self.capabilities.supports_price_verify and self.offer_id is None:
            raise ValueError("price-verifiable booking options require an offer_id")
        return self


class PriceSourceCoverage(ApiModel):
    confirmed_supplier_count: int = Field(ge=0)
    cached_supplier_count: int = Field(default=0, ge=0)
    estimated_supplier_count: int = Field(default=0, ge=0)
    redirect_only_supplier_count: int = Field(default=0, ge=0)
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
    price_amount: Decimal = Field(gt=0, allow_inf_nan=False)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    price_status: PriceStatus = PriceStatus.confirmed
    cabin: Cabin
    baggage_included: bool | None
    booking_url: HttpUrl | None = None
    raw_payload: dict[str, Any] = Field(default_factory=dict)
    last_checked_at: datetime
    expires_at: datetime
    segments: list[Segment] = Field(min_length=1)
    protected_connection: bool = False

    @field_validator("booking_url")
    @classmethod
    def require_safe_booking_url(cls, value: HttpUrl | None) -> HttpUrl | None:
        return validate_booking_url(value)

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
    price_amount: Decimal = Field(gt=0, allow_inf_nan=False)
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
    supplier_results: list[SupplierResult] = Field(default_factory=list)


class RiskAssessment(ApiModel):
    score: int = Field(ge=0, le=100)
    level: RiskLevel
    warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_level_matches_score(self) -> RiskAssessment:
        expected = risk_level_for_score(self.score)
        if self.level != expected:
            raise ValueError(f"risk level {self.level} does not match score {self.score}")
        return self


class Itinerary(ApiModel):
    id: str = Field(min_length=1)
    type: ItineraryType
    total_price: Decimal = Field(gt=0, allow_inf_nan=False)
    currency: str = Field(pattern=r"^[A-Z]{3}$")
    total_duration_minutes: int = Field(gt=0)
    layover_airport: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    layover_gap_minutes: int | None = Field(default=None, ge=0)
    risk_score: int = Field(ge=0, le=100)
    risk_level: RiskLevel
    savings_vs_baseline: Decimal | None = Field(default=None, allow_inf_nan=False)
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
    baseline_price: Decimal | None
    ranked_results: list[Itinerary]


class SearchResults(ApiModel):
    protected_itineraries: list[Itinerary]
    split_ticket_itineraries: list[Itinerary]
    baseline_price: Decimal | None
    ranked_results: list[Itinerary]


class SearchResponse(ApiModel):
    search_id: str
    status: SearchStatus
    results: SearchResults
    errors: list[SearchError]
    explanation: str
    baseline: Itinerary | None
    cheapest: Itinerary | None
    cheapest_split: Itinerary | None
    safest_split: Itinerary | None
    supplier_failures: list[SupplierFailure] = Field(default_factory=list)
    metadata: SearchMetadata
    disclaimer: str = Field(min_length=1)
