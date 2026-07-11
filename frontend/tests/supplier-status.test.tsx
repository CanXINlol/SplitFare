import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ResultsView } from "@/components/results-view";
import { CityCatalogProvider } from "@/lib/city-catalog";
import { I18nProvider } from "@/lib/i18n";
import { getCityCatalog, searchFlights } from "@/lib/api";
import { SearchStatus, Supplier, type CityCatalog, type SearchResponse } from "@/lib/types";

const params = new URLSearchParams({
  originCityId: "city:melbourne-au",
  destinationCityId: "city:shanghai-cn",
  departureDate: "2026-08-12",
  minGapHours: "3",
  maxGapHours: "12",
  passengers: "1",
  cabin: "economy",
});

vi.mock("next/navigation", () => ({ useSearchParams: () => params }));
vi.mock("@/lib/api", () => ({ getCityCatalog: vi.fn(), searchFlights: vi.fn() }));

const catalog: CityCatalog = {
  version: "city-catalog-v1",
  continents: [], countries: [],
  cities: [
    { cityId: "city:melbourne-au", cityNameZh: "墨尔本", cityNameEn: "Melbourne", countryId: "australia", airportCodes: ["MEL", "AVV"], priority: 1, enabled: true },
    { cityId: "city:shanghai-cn", cityNameZh: "上海", cityNameEn: "Shanghai", countryId: "china", airportCodes: ["PVG", "SHA"], priority: 1, enabled: true },
  ],
};

const failedResponse: SearchResponse = {
  searchId: "search-failed", status: SearchStatus.Failed,
  results: { protectedItineraries: [], splitTicketItineraries: [], baselinePrice: null, rankedResults: [] },
  errors: [{ supplier: Supplier.Duffel, origin: "MEL", destination: "PVG", code: "SUPPLIER_TIMEOUT", message: "internal detail" }],
  explanation: "SUPPLIER_SEARCH_FAILED", baseline: null, cheapest: null, cheapestSplit: null, safestSplit: null,
  supplierFailures: [],
  metadata: {
    mode: "sandbox", demoData: false, searchedOriginAirports: ["MEL", "AVV"],
    searchedDestinationAirports: ["PVG", "SHA"], searchedHubs: [], excludedAirports: [],
    supplierErrors: [], routeQueryCount: 4, supplierQueryCount: 4, supplierQueryLimit: 120,
    queryPlanTruncated: false, freshPriceCount: 0, expiredPriceCount: 0,
  },
  disclaimer: "sandbox",
};

function renderResults() {
  return render(<I18nProvider><CityCatalogProvider><ResultsView /></CityCatalogProvider></I18nProvider>);
}

describe("supplier status internationalisation", () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.mocked(getCityCatalog).mockResolvedValue(catalog);
    vi.mocked(searchFlights).mockResolvedValue(failedResponse);
  });

  it("shows stable supplier timeout as English user copy without raw error", async () => {
    renderResults();
    expect(await screen.findByText("The flight supplier timed out. Please try again.")).toBeVisible();
    expect(screen.queryByText("internal detail")).not.toBeInTheDocument();
  });

  it("shows stable supplier timeout as Chinese user copy", async () => {
    window.localStorage.setItem("splitfare:locale:v1", "zh");
    renderResults();
    expect(await screen.findByText("航班供应商请求超时，请重试。")).toBeVisible();
    expect(screen.getByRole("heading", { name: "搜索未能完成" })).toBeVisible();
  });
});
