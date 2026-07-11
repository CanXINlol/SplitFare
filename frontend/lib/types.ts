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
  Failed = "failed",
}

export enum VerificationStatus {
  Verified = "verified",
  Expired = "expired",
  Unavailable = "unavailable",
  NotConfigured = "not_configured",
  Unsupported = "unsupported",
  Timeout = "timeout",
}

export enum PreBookingStatus {
  Unchanged = "unchanged",
  Increased = "increased",
  Decreased = "decreased",
  Unavailable = "unavailable",
  Expired = "expired",
  Timeout = "timeout",
  Unsupported = "unsupported",
}

export enum BookingOptionType {
  Airline = "airline",
  TripCom = "trip_com",
  Skyscanner = "skyscanner",
  Supplier = "supplier",
}

export enum PriceStatus {
  Confirmed = "confirmed",
  Cached = "cached",
  Estimated = "estimated",
  RedirectOnly = "redirect_only",
  Unavailable = "unavailable",
}

export interface SearchRequest {
  originCityId: string;
  destinationCityId: string;
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

export interface Continent {
  continentId: string;
  continentNameZh: string;
  continentNameEn: string;
  priority: number;
}

export interface Country {
  countryId: string;
  continentId: string;
  countryNameZh: string;
  countryNameEn: string;
  countryCode: string;
  priority: number;
}

export interface City {
  cityId: string;
  cityNameZh: string;
  cityNameEn: string;
  countryId: string;
  airportCodes: string[];
  priority: number;
  enabled: boolean;
}

export interface CityCatalog {
  version: string;
  continents: Continent[];
  countries: Country[];
  cities: City[];
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
  marketingAirlineName?: string | null;
  operatingAirlineName?: string | null;
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
  priceStatus: PriceStatus;
  cabin: Cabin;
  baggageIncluded: boolean | null;
  bookingUrl: string | null;
  bookingReference?: string | null;
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
  id: string;
  bookingOptionId: string;
  type: BookingOptionType;
  label: string;
  displayName: string | null;
  supplier: Supplier | null;
  offerId: string | null;
  capabilities: SupplierCapabilities;
  url: string | null;
  bookingUrl: string | null;
  priceAmount: number | null;
  currency: string | null;
  priceStatus: PriceStatus;
  verificationRequired: boolean;
  supportsPriceVerify: boolean;
  trackingId: string | null;
  lastCheckedAt: string | null;
  expiresAt: string | null;
  notes: string[];
  warnings: string[];
}

export interface PriceSourceCoverage {
  confirmedSupplierCount: number;
  cachedSupplierCount: number;
  estimatedSupplierCount: number;
  redirectOnlySupplierCount: number;
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
  priceStatus: PriceStatus;
  priceAmount: number | null;
  currency: string | null;
  checkedAt: string;
  expiresAt: string | null;
  isConfirmed: boolean;
  supported: boolean;
  bookingUrl: string | null;
  message: string;
}

export interface PreBookingVerificationRequest {
  searchId: string;
  itineraryId: string;
  bookingOptionId: string;
}

export interface PreBookingVerificationResponse {
  bookingOptionId: string;
  stillAvailable: boolean;
  currentPrice: number | null;
  previousPrice: number | null;
  currency: string | null;
  priceChanged: boolean;
  bookingUrl: string | null;
  checkedAt: string;
  expiresAt: string | null;
  status: PreBookingStatus;
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
  cheapest: Itinerary | null;
  cheapestSplit: Itinerary | null;
  safestSplit: Itinerary | null;
  supplierFailures: SupplierFailure[];
  metadata: SearchMetadata;
  disclaimer: string;
}

export interface SupplierCapabilities {
  supportsSearch: boolean;
  supportsPriceVerify: boolean;
  supportsBookingUrl: boolean;
  supportsBaggageInfo: boolean;
  supportsSplitTicket: boolean;
  supportsLivePrice: boolean;
  supportsAffiliateLink: boolean;
}

export interface SearchMetadata {
  mode: "mock" | "sandbox" | "live";
  demoData: boolean;
  searchedOriginAirports: string[];
  searchedDestinationAirports: string[];
  searchedHubs: string[];
  excludedAirports: string[];
  supplierErrors: SearchError[];
  routeQueryCount: number;
  supplierQueryCount: number;
  supplierQueryLimit: number;
  queryPlanTruncated: boolean;
  freshPriceCount: number;
  expiredPriceCount: number;
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
