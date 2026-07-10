"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { useEffect, useId, useState } from "react";
import { useForm } from "react-hook-form";
import { searchPlaces } from "@/lib/api";
import { searchSchema, type SearchInput } from "@/lib/schema";
import { Cabin, SortOption, type Place } from "@/lib/types";

const fieldClass = "mt-2 w-full rounded-xl border border-ink/15 bg-white px-4 py-3 outline-none transition focus:border-ink focus:ring-2 focus:ring-mint";

function LocationField({
  label,
  ariaLabel,
  value,
  selectedPlaceId,
  onInput,
  onSelect,
}: {
  label: string;
  ariaLabel: string;
  value: string;
  selectedPlaceId: string;
  onInput: (value: string) => void;
  onSelect: (place: Place) => void;
}) {
  const [suggestions, setSuggestions] = useState<Place[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [lookupError, setLookupError] = useState<string | null>(null);
  const [activeIndex, setActiveIndex] = useState(-1);
  const listboxId = useId();

  useEffect(() => {
    const controller = new AbortController();
    if (value.trim().length < 2) {
      setSuggestions([]);
      setLoading(false);
      setLookupError(null);
      return () => controller.abort();
    }
    setLoading(true);
    setLookupError(null);
    const timer = window.setTimeout(() => {
      searchPlaces(value, controller.signal)
        .then((response) => {
          setSuggestions(response.results);
          setActiveIndex(response.results.length > 0 ? 0 : -1);
          setLookupError(null);
        })
        .catch((error: unknown) => {
          if (error instanceof Error && error.name === "AbortError") return;
          setSuggestions([]);
          setActiveIndex(-1);
          setLookupError(error instanceof Error ? error.message : "Could not search places.");
        })
        .finally(() => {
          if (!controller.signal.aborted) setLoading(false);
        });
    }, 120);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [value]);

  return (
    <label className="relative text-sm font-bold">
      {label}
      <input
        aria-label={ariaLabel}
        className={fieldClass}
        placeholder="City, airport, or place"
        value={value}
        role="combobox"
        aria-autocomplete="list"
        aria-expanded={open && value.trim().length >= 2}
        aria-controls={listboxId}
        aria-activedescendant={activeIndex >= 0 ? `${listboxId}-${activeIndex}` : undefined}
        onChange={(event) => {
          onInput(event.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
        onBlur={() => window.setTimeout(() => setOpen(false), 0)}
        onKeyDown={(event) => {
          if (event.key === "ArrowDown" && suggestions.length > 0) {
            event.preventDefault();
            setOpen(true);
            setActiveIndex((current) => (current + 1) % suggestions.length);
          } else if (event.key === "ArrowUp" && suggestions.length > 0) {
            event.preventDefault();
            setOpen(true);
            setActiveIndex((current) => (current <= 0 ? suggestions.length - 1 : current - 1));
          } else if (event.key === "Enter" && open && activeIndex >= 0 && suggestions[activeIndex]) {
            event.preventDefault();
            onSelect(suggestions[activeIndex]);
            setOpen(false);
          } else if (event.key === "Escape") {
            setOpen(false);
          }
        }}
      />
      <span className="mt-1 block text-xs font-normal text-ink/45">{selectedPlaceId ? "Selected location ready" : "Choose a suggestion before searching"}</span>
      {open && value.trim().length >= 2 && (
        <div id={listboxId} role="listbox" aria-label={`${label} suggestions`} className="absolute z-20 mt-2 w-full overflow-hidden rounded-2xl border border-ink/10 bg-white shadow-card">
          {loading && <p className="px-4 py-3 text-sm text-ink/50">Searching supported places...</p>}
          {lookupError && <p className="px-4 py-3 text-sm text-red-700">{lookupError}</p>}
          {!loading && !lookupError && suggestions.length === 0 && <p className="px-4 py-3 text-sm text-ink/50">No supported places found.</p>}
          {suggestions.map((place, index) => (
            <button
              type="button"
              key={place.id}
              id={`${listboxId}-${index}`}
              role="option"
              aria-selected={index === activeIndex}
              className={`block w-full px-4 py-3 text-left text-sm hover:bg-mint/45 ${index === activeIndex ? "bg-mint/45" : ""}`}
              onMouseDown={(event) => event.preventDefault()}
              onMouseEnter={() => setActiveIndex(index)}
              onClick={() => {
                onSelect(place);
                setOpen(false);
              }}
            >
              <span className="block font-black">{place.displayName}</span>
              {place.type === "city" && place.airportCodes.length > 0 && (
                <span className="block text-xs text-ink/50">Airports: {place.airportCodes.join(", ")}</span>
              )}
            </button>
          ))}
        </div>
      )}
    </label>
  );
}

export function SearchForm() {
  const router = useRouter();
  const [originText, setOriginText] = useState("Melbourne");
  const [destinationText, setDestinationText] = useState("Shanghai");
  const [navigating, setNavigating] = useState(false);
  const defaultDepartureDate = new Date(Date.now() + 33 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);
  const { register, handleSubmit, reset, setValue, watch, formState: { errors } } = useForm<SearchInput>({
    resolver: zodResolver(searchSchema),
    defaultValues: {
      originPlaceId: "city:melbourne-au", destinationPlaceId: "city:shanghai-cn", departureDate: defaultDepartureDate,
      minGapHours: 3, maxGapHours: 12, passengers: 1, cabin: Cabin.Economy,
      maxResults: 20, sort: SortOption.Value,
      checkedBaggageLikelyRequired: false, visaTransitRequirementUnknown: true,
      currency: "AUD", promoCodeNote: "", memberPriceNote: "",
    },
  });
  const originPlaceId = watch("originPlaceId");
  const destinationPlaceId = watch("destinationPlaceId");
  useEffect(() => {
    const saved = window.sessionStorage.getItem("splitfare:last-search");
    if (!saved) return;
    try {
      const value = JSON.parse(saved) as { input?: unknown; originText?: unknown; destinationText?: unknown };
      const parsed = searchSchema.safeParse(value.input);
      if (!parsed.success) return;
      reset(parsed.data);
      if (typeof value.originText === "string") setOriginText(value.originText);
      if (typeof value.destinationText === "string") setDestinationText(value.destinationText);
    } catch {
      window.sessionStorage.removeItem("splitfare:last-search");
    }
  }, [reset]);
  const submit = (input: SearchInput) => {
    if (navigating) return;
    setNavigating(true);
    const entries = Object.entries(input)
      .filter(([, value]) => value !== null && value !== undefined)
      .map(([key, value]) => [key, String(value)] as [string, string]);
    window.sessionStorage.setItem(
      "splitfare:last-search",
      JSON.stringify({ input, originText, destinationText }),
    );
    router.push(`/results?${new URLSearchParams(entries)}`);
  };

  return (
    <form onSubmit={handleSubmit(submit)} className="grid gap-5 rounded-3xl bg-white/90 p-5 shadow-card md:grid-cols-2 lg:grid-cols-4 lg:p-7">
      <input type="hidden" {...register("originPlaceId")} />
      <input type="hidden" {...register("destinationPlaceId")} />
      <LocationField
        label="From"
        ariaLabel="From"
        value={originText}
        selectedPlaceId={originPlaceId}
        onInput={(value) => {
          setOriginText(value);
          setValue("originPlaceId", "", { shouldValidate: true });
        }}
        onSelect={(place) => {
          setOriginText(place.displayName);
          setValue("originPlaceId", place.id, { shouldValidate: true });
        }}
      />
      <LocationField
        label="To"
        ariaLabel="To"
        value={destinationText}
        selectedPlaceId={destinationPlaceId}
        onInput={(value) => {
          setDestinationText(value);
          setValue("destinationPlaceId", "", { shouldValidate: true });
        }}
        onSelect={(place) => {
          setDestinationText(place.displayName);
          setValue("destinationPlaceId", place.id, { shouldValidate: true });
        }}
      />
      <label className="text-sm font-bold">Date<input aria-label="Departure date" type="date" min={new Date().toISOString().slice(0, 10)} className={fieldClass} {...register("departureDate")} /></label>
      <label className="text-sm font-bold">Passengers<input aria-label="Passengers" type="number" min={1} max={9} className={fieldClass} {...register("passengers")} /></label>
      <label className="text-sm font-bold">Minimum gap (hours)<input aria-label="Minimum gap" type="number" min={1} max={24} step="0.5" className={fieldClass} {...register("minGapHours")} /></label>
      <label className="text-sm font-bold">Maximum gap (hours)<input aria-label="Maximum gap" type="number" min={1} max={36} step="0.5" className={fieldClass} {...register("maxGapHours")} /></label>
      <label className="text-sm font-bold">Cabin<select aria-label="Cabin" className={fieldClass} {...register("cabin")}><option value="economy">Economy</option><option value="premium_economy">Premium economy</option><option value="business">Business</option><option value="first">First</option></select></label>
      <label className="text-sm font-bold">Promo code note<input aria-label="Promo code note" className={fieldClass} placeholder="Optional" {...register("promoCodeNote")} /></label>
      <label className="text-sm font-bold">Member price note<input aria-label="Member price note" className={fieldClass} placeholder="Optional" {...register("memberPriceNote")} /></label>
      <button disabled={navigating} className="self-end rounded-xl bg-ink px-5 py-3 font-bold text-white transition hover:-translate-y-0.5 hover:bg-coral disabled:cursor-wait disabled:opacity-60">{navigating ? "Opening search..." : "Search demo fares"}</button>
      {Object.values(errors)[0]?.message && <p role="alert" className="text-sm text-red-700 md:col-span-2 lg:col-span-4">{Object.values(errors)[0]?.message}</p>}
    </form>
  );
}
