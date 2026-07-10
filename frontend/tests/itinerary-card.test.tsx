import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ItineraryCard } from "@/components/itinerary-card";
import { verifyBookingOption } from "@/lib/api";
import { BookingOptionType, Cabin, ItineraryType, PriceStatus, RiskLevel, Supplier, VerificationStatus, type Itinerary, type Segment } from "@/lib/types";
import { I18nProvider } from "@/lib/i18n";

vi.mock("@/lib/api", () => ({ verifyBookingOption: vi.fn() }));

const segment: Segment = {
  id: "one", origin: "MEL", destination: "BKK", departureAt: "2026-08-12T07:00:00Z",
  arrivalAt: "2026-08-12T16:30:00Z", airline: "TG", operatingAirline: "TG", flightNumber: "TG466",
};
const warning = "This is a self-transfer itinerary.";
const connectionWarning = "Your second ticket may not be protected if the first flight is delayed.";

const itinerary: Itinerary = {
  id: "one-two", type: ItineraryType.SplitTicket, totalPrice: 720, currency: "AUD", totalDurationMinutes: 1100,
  layoverAirport: "BKK", layoverGapMinutes: 240, riskLevel: RiskLevel.Medium, riskScore: 45,
  layoverDepartureAirport: null, requiresGroundTransfer: false,
  savingsVsBaseline: 400, valueScore: 72, warnings: [warning, connectionWarning], riskAssessment: { score: 45, level: RiskLevel.Medium, warnings: [warning, connectionWarning] },
  suppliers: [Supplier.MockSky], lastCheckedAt: "2026-08-12T00:00:00Z", expiresAt: "2026-08-12T02:00:00Z",
  priceFreshness: { lastCheckedAt: "2026-08-12T00:00:00Z", expiresAt: "2026-08-12T02:00:00Z", isExpired: false },
  bookingOptions: [{ id: "one-two:supplier:1:offer-one", type: BookingOptionType.Supplier, label: "Verify demo price", displayName: "Ticket with MockSky", supplier: Supplier.MockSky, offerId: "offer-one", capabilities: { supportsSearch: true, supportsPriceVerify: true, supportsBookingUrl: false, supportsBaggageInfo: true, supportsSplitTicket: true, supportsLivePrice: false, supportsAffiliateLink: false }, url: null, bookingUrl: null, priceAmount: 720, currency: "AUD", priceStatus: PriceStatus.Confirmed, verificationRequired: true, trackingId: null, lastCheckedAt: "2026-08-12T00:00:00Z", expiresAt: "2026-08-12T02:00:00Z", notes: [], warnings: [] }],
  priceSourceCoverage: { confirmedSupplierCount: 1, cachedSupplierCount: 0, estimatedSupplierCount: 0, redirectOnlySupplierCount: 0, checkRequiredSupplierCount: 0, unavailableSupplierCount: 0, labels: ["Check on supplier"] },
  segments: [segment],
  offers: [{ id: "offer-one", supplier: Supplier.MockSky, origin: "MEL", destination: "BKK", departureAt: segment.departureAt, arrivalAt: segment.arrivalAt, airline: "TG", operatingAirline: "TG", flightNumber: "TG466", priceAmount: 390, currency: "AUD", priceStatus: PriceStatus.Confirmed, cabin: Cabin.Economy, baggageIncluded: true, bookingUrl: null, lastCheckedAt: "2026-08-12T00:00:00Z", expiresAt: "2026-08-12T02:00:00Z", segments: [segment], protectedConnection: false }],
};

describe("ItineraryCard", () => {
  beforeEach(() => vi.mocked(verifyBookingOption).mockReset());

  it("shows required price, savings, risk, gap, duration and warning", () => {
    render(<I18nProvider><ItineraryCard itinerary={itinerary} searchId="search-1" originCity="Melbourne" destinationCity="Shanghai" /></I18nProvider>);
    expect(screen.getByText("$720")).toBeInTheDocument();
    expect(screen.getByText(/Save \$400/)).toBeInTheDocument();
    expect(screen.getByText(/Medium · 45/i)).toBeInTheDocument();
    expect(screen.getByText("BKK · 4h 0m")).toBeInTheDocument();
    expect(screen.getByText("18h 20m")).toBeInTheDocument();
    expect(screen.getByText(/delay on the first ticket may not protect/i)).toBeInTheDocument();
  });

  it("verifies only the canonical booking option identifiers", async () => {
    vi.mocked(verifyBookingOption).mockResolvedValue({
      stillAvailable: true, currentPrice: 390, previousPrice: 390, currency: "AUD",
      priceChanged: false, bookingUrl: null, checkedAt: "2026-08-12T00:01:00Z",
      expiresAt: "2026-08-12T00:06:00Z", status: VerificationStatus.Verified,
      message: "Verified against deterministic mock data.", canContinue: false,
      requiresPriceCheck: false,
    });
    render(<I18nProvider><ItineraryCard itinerary={itinerary} searchId="search-1" originCity="Melbourne" destinationCity="Shanghai" /></I18nProvider>);
    fireEvent.click(screen.getByRole("button", { name: "Verify demo price" }));
    await waitFor(() => expect(verifyBookingOption).toHaveBeenCalledWith({
      searchId: "search-1",
      itineraryId: "one-two",
      bookingOptionId: "one-two:supplier:1:offer-one",
    }));
    expect(await screen.findByRole("dialog", { name: /Check before continuing/i })).toBeVisible();
    expect(screen.getByText(/No demo price change/)).toBeVisible();
  });
});
