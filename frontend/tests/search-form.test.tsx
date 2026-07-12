import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AppShell } from "@/components/app-shell";
import { SearchForm } from "@/components/search-form";
import { CityCatalogProvider } from "@/lib/city-catalog";
import { I18nProvider } from "@/lib/i18n";
import { getCityCatalog } from "@/lib/api";
import type { CityCatalog } from "@/lib/types";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));
vi.mock("@/lib/api", () => ({ getCityCatalog: vi.fn() }));

const catalog: CityCatalog = {
  version: "city-catalog-v1",
  continents: [
    { continentId: "asia", continentNameZh: "亚洲", continentNameEn: "Asia", priority: 1 },
    { continentId: "oceania", continentNameZh: "大洋洲", continentNameEn: "Oceania", priority: 2 },
  ],
  countries: [
    { countryId: "china", continentId: "asia", countryNameZh: "中国", countryNameEn: "China", countryCode: "CN", priority: 1 },
    { countryId: "australia", continentId: "oceania", countryNameZh: "澳大利亚", countryNameEn: "Australia", countryCode: "AU", priority: 1 },
  ],
  cities: [
    { cityId: "city:shanghai-cn", cityNameZh: "上海", cityNameEn: "Shanghai", countryId: "china", airportCodes: ["PVG", "SHA"], priority: 1, enabled: true },
    { cityId: "city:beijing-cn", cityNameZh: "北京", cityNameEn: "Beijing", countryId: "china", airportCodes: ["PEK", "PKX"], priority: 2, enabled: true },
    { cityId: "city:melbourne-au", cityNameZh: "墨尔本", cityNameEn: "Melbourne", countryId: "australia", airportCodes: ["MEL", "AVV"], priority: 1, enabled: true },
  ],
};

function renderForm(shell = false) {
  return render(<I18nProvider><CityCatalogProvider>{shell ? <AppShell><SearchForm /></AppShell> : <SearchForm />}</CityCatalogProvider></I18nProvider>);
}

describe("structured city search", () => {
  beforeEach(() => { push.mockReset(); vi.mocked(getCityCatalog).mockResolvedValue(catalog); window.sessionStorage.clear(); window.localStorage.clear(); });

  it("contains no free-text location or IATA input", async () => {
    renderForm();
    await screen.findByRole("button", { name: /From: Melbourne/i });
    expect(screen.queryByRole("combobox", { name: /from/i })).not.toBeInTheDocument();
    expect(document.querySelector('input[name="originCityId"]')).toHaveValue("city:melbourne-au");
  });

  it("selects a city through continent country and city hierarchy", async () => {
    renderForm();
    fireEvent.click(await screen.findByRole("button", { name: /To: Shanghai/i }));
    fireEvent.click(screen.getByRole("button", { name: /Beijing/ }));
    expect(document.querySelector('input[name="destinationCityId"]')).toHaveValue("city:beijing-cn");
  });

  it("keeps selected city ids when language changes", async () => {
    renderForm(true);
    await screen.findByRole("button", { name: /From: Melbourne/i });
    fireEvent.click(screen.getByRole("button", { name: "Switch language" }));
    expect(await screen.findByRole("button", { name: /出发城市: 墨尔本/ })).toBeVisible();
    expect(document.querySelector('input[name="originCityId"]')).toHaveValue("city:melbourne-au");
  });

  it("submits city ids and versioned browser state", async () => {
    renderForm();
    fireEvent.click(await screen.findByRole("button", { name: /Discover routes/ }));
    await waitFor(() => expect(push).toHaveBeenCalled());
    expect(push.mock.calls[0][0]).toContain("originCityId=city%3Amelbourne-au");
    expect(window.sessionStorage.getItem("splitfare:route-search:v3")).toContain("city:shanghai-cn");
  });

  it("removes the legacy search-state key", async () => {
    window.sessionStorage.setItem("splitfare:last-search", "legacy");
    renderForm();
    await waitFor(() => expect(window.sessionStorage.getItem("splitfare:last-search")).toBeNull());
  });
});
