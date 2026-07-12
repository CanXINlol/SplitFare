import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AppShell } from "@/components/app-shell";
import { ResultsView } from "@/components/results-view";
import { CityCatalogProvider } from "@/lib/city-catalog";
import { I18nProvider } from "@/lib/i18n";
import { discoverRoutes, getCityCatalog } from "@/lib/api";
import { Cabin, ProviderLinkType, RiskLevel, SearchStatus, type CityCatalog, type RouteDiscoveryResponse } from "@/lib/types";

const params = new URLSearchParams({ originCityId: "city:melbourne-au", destinationCityId: "city:shanghai-cn", departureDate: "2026-08-12", minGapHours: "3", maxGapHours: "12", passengers: "1", cabin: "economy", maxResults: "20", sort: "best_route" });
vi.mock("next/navigation", () => ({ useSearchParams: () => params }));
vi.mock("@/lib/api", () => ({ getCityCatalog: vi.fn(), discoverRoutes: vi.fn() }));

const catalog: CityCatalog = { version: "city-catalog-v1", continents: [], countries: [], cities: [
  { cityId: "city:melbourne-au", cityNameZh: "墨尔本", cityNameEn: "Melbourne", countryId: "australia", airportCodes: ["MEL", "AVV"], priority: 1, enabled: true },
  { cityId: "city:shanghai-cn", cityNameZh: "上海", cityNameEn: "Shanghai", countryId: "china", airportCodes: ["PVG", "SHA"], priority: 1, enabled: true },
  { cityId: "city:singapore-sg", cityNameZh: "新加坡", cityNameEn: "Singapore", countryId: "singapore", airportCodes: ["SIN"], priority: 1, enabled: true },
] };
const link = (id: string, origin: string, destination: string) => ({ id, provider: "google-flights", providerDisplayName: "Google Flights", originAirport: origin, destinationAirport: destination, departureDate: "2026-08-12", passengers: 1, cabin: Cabin.Economy, searchUrl: "https://www.google.com/travel/flights", linkType: ProviderLinkType.ManualSearchRequired, supportedLocale: ["en", "zh"], warnings: ["MANUAL_INPUT_REQUIRED"] });
const response: RouteDiscoveryResponse = { discoveryId: "one", status: SearchStatus.Complete, routes: [{
  id: "route:mel-sin-pvg", signature: "MEL|SIN|PVG", candidateRoute: true,
  originCityId: "city:melbourne-au", destinationCityId: "city:shanghai-cn", originAirport: "MEL",
  hubCityId: "city:singapore-sg", hubArrivalAirport: "SIN", hubDepartureAirport: "SIN", destinationAirport: "PVG",
  departureDate: "2026-08-12", suggestedMinGapHours: 3, suggestedMaxGapHours: 12, separateTicketCount: 2,
  requiresBaggageRecheck: true, mayRequireImmigration: true, crossAirport: false, directDistanceKm: 8000,
  splitDistanceKm: 8500, detourRatio: 1.06, detourLevel: "low", routeScore: 88,
  risk: { structuralScore: 65, level: RiskLevel.High, structuralWarnings: ["SELF_TRANSFER", "SEPARATE_TICKETS"], scheduleDependentWarnings: ["SCHEDULE_NOT_CHECKED", "VERIFY_GAP_ON_PROVIDER"], unknownWarnings: ["IMMIGRATION_UNKNOWN"] },
  recommendationReasons: ["MAJOR_HUB", "DETOUR_LOW", "SAME_AIRPORT_TRANSFER"],
  firstLegLinks: [link("one", "MEL", "SIN")], secondLegLinks: [link("two", "SIN", "PVG")], fullRouteLinks: [],
}], metadata: { originAirports: ["MEL", "AVV"], destinationAirports: ["PVG", "SHA"], selectedHubs: ["city:singapore-sg"], generatedRouteCount: 1, filteredExtremeDetourCount: 0, priceDataAvailable: false }, disclaimerCode: "ROUTE_DISCOVERY_NO_LIVE_PRICES" };

function renderResults(shell = false) { return render(<I18nProvider><CityCatalogProvider>{shell ? <AppShell><ResultsView /></AppShell> : <ResultsView />}</CityCatalogProvider></I18nProvider>); }

describe("route discovery results", () => {
  beforeEach(() => { localStorage.clear(); vi.mocked(getCityCatalog).mockReset(); vi.mocked(discoverRoutes).mockReset(); vi.mocked(getCityCatalog).mockResolvedValue(catalog); vi.mocked(discoverRoutes).mockResolvedValue(response); });
  it("shows an English candidate route with two leg search buttons and no fare", async () => {
    renderResults(); expect((await screen.findAllByText(/Melbourne/))[0]).toBeVisible();
    expect(screen.getAllByText(/Singapore/).length).toBeGreaterThan(0); expect(screen.getAllByText(/Shanghai/).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("button", { name: /Google Flights/ })).toHaveLength(2);
    expect(screen.getAllByText(/does not retrieve live prices/).length).toBeGreaterThan(0);
    expect(screen.queryByText(/Confirmed price/)).not.toBeInTheDocument();
  });
  it("shows Chinese route explanations", async () => {
    localStorage.setItem("splitfare:locale:v1", "zh"); renderResults();
    expect((await screen.findAllByText(/墨尔本/))[0]).toBeVisible(); expect(screen.getAllByText(/当前版本负责发现潜在的低价拆票路线/).length).toBeGreaterThan(0);
    expect(screen.getByText("系统没有检查具体航班时刻。")).toBeVisible();
  });
  it("keeps route results when switching language without rediscovery", async () => {
    renderResults(true); await screen.findAllByText(/Melbourne/); expect(discoverRoutes).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole("button", { name: "Switch language" }));
    expect((await screen.findAllByText(/墨尔本/))[0]).toBeVisible(); expect(discoverRoutes).toHaveBeenCalledTimes(1);
  });
  it("saves manual prices locally and restores them after remount", async () => {
    const first = renderResults(); await screen.findAllByText(/Melbourne/);
    fireEvent.click(screen.getByRole("button", { name: "Compare prices manually" }));
    fireEvent.change(screen.getByLabelText("First-leg price"), { target: { value: "420" } });
    fireEvent.change(screen.getByLabelText("Second-leg price"), { target: { value: "260" } });
    fireEvent.click(screen.getByRole("button", { name: "Save comparison" }));
    await waitFor(() => expect(localStorage.getItem("splitfare:manual-comparisons:v1")).toContain("420"));
    first.unmount(); renderResults(); await screen.findAllByText(/Melbourne/);
    fireEvent.click(screen.getByRole("button", { name: "Compare prices manually" }));
    expect(screen.getByLabelText("First-leg price")).toHaveValue("420");
  });
});
