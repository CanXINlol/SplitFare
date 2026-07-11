import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ItineraryCard } from "@/components/itinerary-card";
import { AppShell } from "@/components/app-shell";
import { verifyBookingOption } from "@/lib/api";
import { BookingOptionType, Cabin, ItineraryType, PreBookingStatus, PriceStatus, RiskLevel, Supplier, type Itinerary, type Segment } from "@/lib/types";
import { I18nProvider } from "@/lib/i18n";

vi.mock("@/lib/api", () => ({ verifyBookingOption: vi.fn(), confirmProviderRedirect: vi.fn() }));

const segment: Segment = {
  id: "one", origin: "MEL", destination: "BKK", departureAt: "2026-08-12T07:00:00Z",
  arrivalAt: "2026-08-12T16:30:00Z", airline: "TG", operatingAirline: "TG", operatingAirlineName: "Thai Airways", flightNumber: "TG466",
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
  bookingOptions: [{ id: "one-two:supplier:1:offer-one", bookingOptionId: "one-two:supplier:1:offer-one", type: BookingOptionType.Supplier, label: "Verify demo price", displayName: "Ticket with MockSky", supplier: Supplier.MockSky, offerId: "offer-one", capabilities: { supportsSearch: true, supportsPriceVerify: true, supportsBookingUrl: false, supportsBaggageInfo: true, supportsSplitTicket: true, supportsLivePrice: false, supportsAffiliateLink: false }, supportsPriceVerify: true, url: null, bookingUrl: null, priceAmount: 720, currency: "AUD", priceStatus: PriceStatus.Confirmed, verificationRequired: true, trackingId: null, lastCheckedAt: "2026-08-12T00:00:00Z", expiresAt: "2026-08-12T02:00:00Z", notes: [], warnings: [] }],
  priceSourceCoverage: { confirmedSupplierCount: 1, cachedSupplierCount: 0, estimatedSupplierCount: 0, redirectOnlySupplierCount: 0, checkRequiredSupplierCount: 0, unavailableSupplierCount: 0, labels: ["Check on supplier"] },
  segments: [segment],
  offers: [{ id: "offer-one", supplier: Supplier.MockSky, origin: "MEL", destination: "BKK", departureAt: segment.departureAt, arrivalAt: segment.arrivalAt, airline: "TG", operatingAirline: "TG", flightNumber: "TG466", priceAmount: 390, currency: "AUD", priceStatus: PriceStatus.Confirmed, cabin: Cabin.Economy, baggageIncluded: true, bookingUrl: null, lastCheckedAt: "2026-08-12T00:00:00Z", expiresAt: "2026-08-12T02:00:00Z", segments: [segment], protectedConnection: false }],
};

describe("ItineraryCard", () => {
  beforeEach(() => vi.mocked(verifyBookingOption).mockReset());

  it("shows required price, savings, risk, gap, duration and warning", () => {
    render(<I18nProvider><ItineraryCard itinerary={itinerary} searchId="search-1" originCity="Melbourne" destinationCity="Shanghai" mode="mock" /></I18nProvider>);
    expect(screen.getByText("$720")).toBeInTheDocument();
    expect(screen.getByText(/Save \$400/)).toBeInTheDocument();
    expect(screen.getByText(/Medium · 45/i)).toBeInTheDocument();
    expect(screen.getByText("BKK · 4h 0m")).toBeInTheDocument();
    expect(screen.getByText("18h 20m")).toBeInTheDocument();
    expect(screen.getByText("Operated by Thai Airways")).toBeVisible();
    expect(screen.getByText(/delay on the first ticket may not protect/i)).toBeInTheDocument();
  });

  it("verifies only the canonical booking option identifiers", async () => {
    vi.mocked(verifyBookingOption).mockResolvedValue({
      bookingOptionId: "one-two:supplier:1:offer-one", stillAvailable: true, currentPrice: 390, previousPrice: 390, currency: "AUD",
      priceChanged: false, bookingUrl: null, checkedAt: "2026-08-12T00:01:00Z",
      expiresAt: "2026-08-12T00:06:00Z", status: PreBookingStatus.Unchanged,
      message: "Verified against deterministic mock data.", canContinue: false,
      requiresPriceCheck: false,
    });
    render(<I18nProvider><ItineraryCard itinerary={itinerary} searchId="search-1" originCity="Melbourne" destinationCity="Shanghai" mode="mock" /></I18nProvider>);
    fireEvent.click(screen.getByRole("button", { name: "Verify price" }));
    await waitFor(() => expect(verifyBookingOption).toHaveBeenCalledWith({
      searchId: "search-1",
      itineraryId: "one-two",
      bookingOptionId: "one-two:supplier:1:offer-one",
    }));
    expect(await screen.findByRole("dialog", { name: /Check before continuing/i })).toBeVisible();
    expect(screen.getAllByText(/Price unchanged/).length).toBeGreaterThan(0);
  });

  it("labels sandbox data without presenting it as live", () => {
    render(<I18nProvider><ItineraryCard itinerary={itinerary} searchId="search-1" originCity="Melbourne" destinationCity="Shanghai" mode="sandbox" /></I18nProvider>);
    expect(screen.getByText("Duffel sandbox data")).toBeVisible();
    expect(screen.queryByText("Live supplier prices")).not.toBeInTheDocument();
  });

  it("shows increased prices without automatically redirecting", async () => {
    vi.mocked(verifyBookingOption).mockResolvedValue({
      bookingOptionId: "one-two:supplier:1:offer-one", stillAvailable: true,
      currentPrice: 760, previousPrice: 720, currency: "AUD", priceChanged: true,
      bookingUrl: "https://checkout.duffel.test/session", checkedAt: "2026-08-12T00:01:00Z",
      expiresAt: "2026-08-12T00:06:00Z", status: PreBookingStatus.Increased,
      message: "VERIFY_INCREASED", canContinue: true, requiresPriceCheck: false,
    });
    render(<I18nProvider><ItineraryCard itinerary={itinerary} searchId="search-1" originCity="Melbourne" destinationCity="Shanghai" mode="sandbox" /></I18nProvider>);
    fireEvent.click(screen.getByRole("button", { name: "Verify price" }));
    expect(await screen.findByText("Price increased")).toBeVisible();
    expect(screen.getAllByText("$720").length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText("$760")).toBeVisible();
    expect(screen.getByRole("button", { name: "Continue to supplier" })).toBeEnabled();
  });

  it("allows timeout retry and Escape keyboard dismissal", async () => {
    vi.mocked(verifyBookingOption).mockResolvedValue({
      bookingOptionId: "one-two:supplier:1:offer-one", stillAvailable: false,
      currentPrice: null, previousPrice: 720, currency: "AUD", priceChanged: false,
      bookingUrl: null, checkedAt: "2026-08-12T00:01:00Z", expiresAt: null,
      status: PreBookingStatus.Timeout, message: "VERIFY_TIMEOUT", canContinue: false,
      requiresPriceCheck: false,
    });
    render(<I18nProvider><ItineraryCard itinerary={itinerary} searchId="search-1" originCity="Melbourne" destinationCity="Shanghai" mode="mock" /></I18nProvider>);
    fireEvent.click(screen.getByRole("button", { name: "Verify price" }));
    const retry = await screen.findByRole("button", { name: "Retry verification" });
    fireEvent.click(retry);
    await waitFor(() => expect(verifyBookingOption).toHaveBeenCalledTimes(2));
    await waitFor(() => expect(screen.getByRole("button", { name: "Retry verification" })).toBeEnabled());
    fireEvent.keyDown(window, { key: "Escape" });
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  });

  it("keeps unsupported verification open and translates it after language switch", async () => {
    const redirectOption = {
      ...itinerary.bookingOptions[0], supportsPriceVerify: false,
      capabilities: { ...itinerary.bookingOptions[0].capabilities, supportsPriceVerify: false, supportsBookingUrl: true },
      bookingUrl: "https://provider.test/book", url: "https://provider.test/book",
      priceAmount: null, currency: null, priceStatus: PriceStatus.RedirectOnly,
    };
    vi.mocked(verifyBookingOption).mockResolvedValue({
      bookingOptionId: redirectOption.bookingOptionId, stillAvailable: true,
      currentPrice: null, previousPrice: null, currency: null, priceChanged: false,
      bookingUrl: redirectOption.bookingUrl, checkedAt: "2026-08-12T00:01:00Z", expiresAt: null,
      status: PreBookingStatus.Unsupported, message: "VERIFY_UNSUPPORTED", canContinue: true,
      requiresPriceCheck: true,
    });
    render(<I18nProvider><AppShell><ItineraryCard itinerary={{ ...itinerary, bookingOptions: [redirectOption] }} searchId="search-1" originCity="Melbourne" destinationCity="Shanghai" mode="live" /></AppShell></I18nProvider>);
    fireEvent.click(screen.getByRole("button", { name: "Check supplier" }));
    expect(await screen.findByText("This provider does not support pre-redirect price verification. The final price is determined by the provider.")).toBeVisible();
    fireEvent.click(screen.getByRole("button", { name: "Switch language" }));
    expect(screen.getByRole("dialog")).toBeVisible();
    expect(screen.getByText("该供应商不支持跳转前验价，最终价格以供应商页面为准。")).toBeVisible();
  });
});
