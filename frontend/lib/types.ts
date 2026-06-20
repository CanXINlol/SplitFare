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

export interface SearchRequest {
  origin: string;
  destination: string;
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
}

export interface Segment {
  id: string;
  origin: string;
  destination: string;
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
  layoverDepartureAirport: string | null;
  requiresGroundTransfer: boolean;
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
