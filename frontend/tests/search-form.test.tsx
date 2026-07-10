import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { SearchForm } from "@/components/search-form";
import { searchPlaces } from "@/lib/api";
import { PlaceType, type Place } from "@/lib/types";

const push = vi.fn();

vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));
vi.mock("@/lib/api", () => ({ searchPlaces: vi.fn() }));

const places: Place[] = [
  {
    id: "airport:MEL", type: PlaceType.Airport, name: "Melbourne Airport",
    displayName: "Melbourne Airport (MEL)", country: "Australia", aliases: [],
    airportCodes: ["MEL"], iataCode: "MEL", isMajorHub: true, priority: 1,
  },
  {
    id: "city:melbourne-au", type: PlaceType.City, name: "Melbourne",
    displayName: "Melbourne, Australia", country: "Australia", aliases: [{ value: "墨尔本", locale: null }],
    airportCodes: ["MEL", "AVV"], iataCode: null, isMajorHub: true, priority: 1,
  },
  {
    id: "airport:AVV", type: PlaceType.Airport, name: "Avalon Airport",
    displayName: "Avalon Airport (AVV)", country: "Australia", aliases: [],
    airportCodes: ["AVV"], iataCode: "AVV", isMajorHub: false, priority: 4,
  },
];

describe("SearchForm location autocomplete", () => {
  beforeEach(() => {
    push.mockReset();
    vi.mocked(searchPlaces).mockReset();
  });

  it("shows related MEL results and supports Enter selection", async () => {
    vi.mocked(searchPlaces).mockResolvedValue({ results: places });
    render(<SearchForm />);
    const input = screen.getByRole("combobox", { name: "From" });
    fireEvent.change(input, { target: { value: "mel" } });

    await waitFor(() => expect(searchPlaces).toHaveBeenCalledWith("mel", expect.any(AbortSignal)));
    expect(await screen.findByRole("option", { name: /Melbourne Airport/ })).toBeVisible();
    expect(screen.getByRole("option", { name: /Melbourne, Australia/ })).toBeVisible();
    expect(screen.getByRole("option", { name: /Avalon Airport/ })).toBeVisible();

    fireEvent.keyDown(input, { key: "Enter" });
    expect(input).toHaveValue("Melbourne Airport (MEL)");
    expect(document.querySelector<HTMLInputElement>('input[name="originPlaceId"]')).toHaveValue("airport:MEL");
  });

  it("selects a Chinese city alias as a stable city place id", async () => {
    vi.mocked(searchPlaces).mockResolvedValue({ results: [places[1]] });
    render(<SearchForm />);
    const input = screen.getByRole("combobox", { name: "From" });
    fireEvent.change(input, { target: { value: "墨尔本" } });
    fireEvent.click(await screen.findByRole("option", { name: /Melbourne, Australia/ }));
    expect(document.querySelector<HTMLInputElement>('input[name="originPlaceId"]')).toHaveValue("city:melbourne-au");
  });

  it("renders a non-blocking lookup error", async () => {
    vi.mocked(searchPlaces).mockRejectedValue(new Error("API unavailable"));
    render(<SearchForm />);
    fireEvent.change(screen.getByRole("combobox", { name: "From" }), { target: { value: "mel" } });
    expect(await screen.findByText("API unavailable")).toBeVisible();
  });
});
