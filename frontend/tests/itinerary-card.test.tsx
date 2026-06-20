import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ItineraryCard } from "@/components/itinerary-card";
import { Cabin, ItineraryType, RiskLevel, Supplier, type Itinerary, type Segment } from "@/lib/types";

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
  segments: [segment],
  offers: [{ id: "offer-one", supplier: Supplier.MockSky, origin: "MEL", destination: "BKK", departureAt: segment.departureAt, arrivalAt: segment.arrivalAt, airline: "TG", operatingAirline: "TG", flightNumber: "TG466", priceAmount: 390, currency: "AUD", cabin: Cabin.Economy, baggageIncluded: true, bookingUrl: null, rawPayload: { fixture: "one" }, lastCheckedAt: "2026-08-12T00:00:00Z", expiresAt: "2026-08-12T02:00:00Z", segments: [segment], protectedConnection: false }],
};

describe("ItineraryCard", () => {
  it("shows required price, savings, risk, gap, duration and warning", () => {
    render(<ItineraryCard itinerary={itinerary} />);
    expect(screen.getByText("$720")).toBeInTheDocument();
    expect(screen.getByText(/Save \$400/)).toBeInTheDocument();
    expect(screen.getByText(/medium risk/i)).toBeInTheDocument();
    expect(screen.getByText("4h at BKK")).toBeInTheDocument();
    expect(screen.getByText("18h 20m")).toBeInTheDocument();
    expect(screen.getByText(/second ticket may not be protected/i)).toBeInTheDocument();
  });
});
