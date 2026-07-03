export enum Supplier {
  MockSky = "MockSky",
  DemoAir = "DemoAir",
  BudgetDemo = "BudgetDemo",
  Duffel = "Duffel",
  Skyscanner = "Skyscanner",
  TripComAffiliate = "TripComAffiliate",
}

export enum ItineraryType {
  Protected = "protected",
  SplitTicket = "split_ticket",
}

export enum RiskLevel {
  Low = "low",
  Medium = "medium",
  High = "high",
  Extreme = "extreme",
}

export enum Cabin {
  Economy = "economy",
  PremiumEconomy = "premium_economy",
  Business = "business",
  First = "first",
}

export enum SortOption {
  Value = "value",
  Cheapest = "cheapest",
}

export enum SearchStatus {
  Complete = "complete",
  Partial = "partial",
  Empty = "empty",
}

export enum PlaceType {
  City = "city",
  Airport = "airport",
  MetroArea = "metro_area",
}

export enum VerificationStatus {
  Verified = "verified",
  Expired = "expired",
  Unavailable = "unavailable",
  NotConfigured = "not_configured",
}

export enum BookingOptionType {
  Airline = "airline",
  TripCom = "trip_com",
  Skyscanner = "skyscanner",
  Supplier = "supplier",
}

export enum PriceConfidence {
  Confirmed = "confirmed",
  CheckRequired = "check_required",
  Unavailable = "unavailable",
}

export interface SearchRequest {
  originPlaceId: string;
  destinationPlaceId: string;
  departureDate: string;
  minGapHours: number;
  maxGapHours: number;
  passengers: number;
  cabin: Cabin;
  maxResults: number;
  sort: SortOption;
  checkedBaggageLikelyRequired: boolean;
  visaTransitRequirementUnknown: boolean;
  currency: string;
  candidateHubs?: string[];
  promoCodeNote?: string | null;
  memberPriceNote?: string | null;
}

export interface PlaceAlias {
  value: string;
  locale: string | null;
}

export interface CandidateAirport {
  iataCode: string;
  name: string;
  displayName: string;
  city: string;
  country: string;
  isPrimary: boolean;
  international: boolean;
  priority: number;
  distanceToCityKm: number;
  hasMockFlightData: boolean;
}

export interface Place {
  id: string;
  type: PlaceType;
  name: string;
  displayName: string;
  country: string;
  aliases: PlaceAlias[];
  airportCodes: string[];
  iataCode: string | null;
  isMajorHub: boolean;
  priority: number;
}

export interface PlaceSearchResponse {
  results: Place[];
}

export interface ResolvedPlace {
  placeId: string;
  type: PlaceType;
  displayName: string;
  country: string;
  airports: CandidateAirport[];
}

export interface Segment {
  id: string;
  origin: string;
  destination: string;
  originDisplay?: string | null;
  destinationDisplay?: string | null;
  departureAt: string;
  arrivalAt: string;
  airline: string;
  operatingAirline: string;
  flightNumber: string;
}

export interface NormalizedFlightOffer {
  id: string;
  supplier: Supplier;
  origin: string;
  destination: string;
  departureAt: string;
  arrivalAt: string;
  airline: string;
  operatingAirline: string;
  flightNumber: string;
  priceAmount: number;
  currency: string;
  cabin: Cabin;
  baggageIncluded: boolean | null;
  bookingUrl: string | null;
  rawPayload?: Record<string, unknown>;
  lastCheckedAt: string;
  expiresAt: string;
  segments: Segment[];
  protectedConnection: boolean;
}

export interface RiskAssessment {
  score: number;
  level: RiskLevel;
  warnings: string[];
}

export interface PriceFreshness {
  lastCheckedAt: string;
  expiresAt: string;
  isExpired: boolean;
}

export interface BookingOption {
  type: BookingOptionType;
  label: string;
  supplier: Supplier | null;
  url: string | null;
  priceAmount: number | null;
  currency: string | null;
  priceConfidence: PriceConfidence;
  trackingId: string | null;
  lastCheckedAt: string | null;
  expiresAt: string | null;
  notes: string[];
}

export interface PriceSourceCoverage {
  confirmedSupplierCount: number;
  checkRequiredSupplierCount: number;
  unavailableSupplierCount: number;
  labels: string[];
}

export interface Itinerary {
  id: string;
  type: ItineraryType;
  totalPrice: number;
  currency: string;
  totalDurationMinutes: number;
  layoverAirport: string | null;
  layoverGapMinutes: number | null;
  riskScore: number;
  riskLevel: RiskLevel;
  savingsVsBaseline: number | null;
  valueScore: number;
  warnings: string[];
  segments: Segment[];
  offers: NormalizedFlightOffer[];
  riskAssessment: RiskAssessment;
  suppliers: Supplier[];
  lastCheckedAt: string;
  expiresAt: string;
  priceFreshness: PriceFreshness;
  bookingOptions: BookingOption[];
  priceSourceCoverage: PriceSourceCoverage | null;
  layoverDepartureAirport: string | null;
  requiresGroundTransfer: boolean;
}

export interface PriceVerification {
  offerId: string;
  supplier: Supplier;
  status: VerificationStatus;
  priceAmount: number | null;
  currency: string | null;
  checkedAt: string;
  expiresAt: string | null;
  isConfirmed: boolean;
  message: string;
}

export interface PreBookingVerificationRequest {
  searchId?: string | null;
  itineraryId: string;
  offerId?: string | null;
  supplier: Supplier;
  bookingOptionType: BookingOptionType;
  bookingOptionLabel: string;
  previousPrice?: number | null;
  currency?: string | null;
  bookingUrl?: string | null;
  trackingId?: string | null;
}

export interface PreBookingVerificationResponse {
  stillAvailable: boolean;
  currentPrice: number | null;
  previousPrice: number | null;
  currency: string | null;
  priceChanged: boolean;
  bookingUrl: string | null;
  checkedAt: string;
  expiresAt: string | null;
  status: VerificationStatus;
  message: string;
  canContinue: boolean;
  requiresPriceCheck: boolean;
}

export interface SearchResponse {
  searchId: string;
  status: SearchStatus;
  results: SearchResults;
  errors: SearchError[];
  explanation: string;
  baseline: Itinerary | null;
  cheapestSplit: Itinerary | null;
  safestSplit: Itinerary | null;
  ranked: Itinerary[];
  protectedItineraries: Itinerary[];
  splitTicketItineraries: Itinerary[];
  baselinePrice: number | null;
  rankedResults: Itinerary[];
  supplierFailures: SupplierFailure[];
  disclaimer: string;
}

export interface SearchResults {
  protectedItineraries: Itinerary[];
  splitTicketItineraries: Itinerary[];
  baselinePrice: number | null;
  rankedResults: Itinerary[];
}

export interface SearchError {
  supplier: Supplier | null;
  origin: string | null;
  destination: string | null;
  code: string;
  message: string;
}

export interface SupplierFailure {
  supplier: Supplier;
  errorType: string;
  message: string;
}
