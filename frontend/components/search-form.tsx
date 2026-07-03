"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
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

  useEffect(() => {
    const controller = new AbortController();
    if (value.trim().length < 2) {
      setSuggestions([]);
      return () => controller.abort();
    }
    const timer = window.setTimeout(() => {
      searchPlaces(value, controller.signal)
        .then((response) => setSuggestions(response.results))
        .catch(() => setSuggestions([]));
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
        onChange={(event) => {
          onInput(event.target.value);
          setOpen(true);
        }}
        onFocus={() => setOpen(true)}
      />
      <span className="mt-1 block text-xs font-normal text-ink/45">{selectedPlaceId ? "Selected location ready" : "Choose a suggestion before searching"}</span>
      {open && suggestions.length > 0 && (
        <div className="absolute z-20 mt-2 w-full overflow-hidden rounded-2xl border border-ink/10 bg-white shadow-card">
          {suggestions.map((place) => (
            <button
              type="button"
              key={place.id}
              className="block w-full px-4 py-3 text-left text-sm hover:bg-mint/45"
              onMouseDown={(event) => event.preventDefault()}
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
  const { register, handleSubmit, setValue, watch, formState: { errors } } = useForm<SearchInput>({
    resolver: zodResolver(searchSchema),
    defaultValues: {
      originPlaceId: "city:melbourne-au", destinationPlaceId: "city:shanghai-cn", departureDate: "2026-08-12",
      minGapHours: 3, maxGapHours: 12, passengers: 1, cabin: Cabin.Economy,
      maxResults: 20, sort: SortOption.Value,
      checkedBaggageLikelyRequired: false, visaTransitRequirementUnknown: true,
      currency: "AUD", promoCodeNote: "", memberPriceNote: "",
    },
  });
  const originPlaceId = watch("originPlaceId");
  const destinationPlaceId = watch("destinationPlaceId");
  const submit = (input: SearchInput) => router.push(`/results?${new URLSearchParams(Object.entries(input).map(([key, value]) => [key, String(value)]))}`);

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
      <label className="text-sm font-bold">Departure<input aria-label="Departure date" type="date" className={fieldClass} {...register("departureDate")} /></label>
      <label className="text-sm font-bold">Passengers<input aria-label="Passengers" type="number" className={fieldClass} {...register("passengers")} /></label>
      <label className="text-sm font-bold">Minimum gap (hours)<input aria-label="Minimum gap" type="number" step="0.5" className={fieldClass} {...register("minGapHours")} /></label>
      <label className="text-sm font-bold">Maximum gap (hours)<input aria-label="Maximum gap" type="number" step="0.5" className={fieldClass} {...register("maxGapHours")} /></label>
      <label className="text-sm font-bold">Cabin<select aria-label="Cabin" className={fieldClass} {...register("cabin")}><option value="economy">Economy</option><option value="premium_economy">Premium economy</option><option value="business">Business</option><option value="first">First</option></select></label>
      <label className="text-sm font-bold">Promo code note<input aria-label="Promo code note" className={fieldClass} placeholder="Optional" {...register("promoCodeNote")} /></label>
      <label className="text-sm font-bold">Member price note<input aria-label="Member price note" className={fieldClass} placeholder="Optional" {...register("memberPriceNote")} /></label>
      <button className="self-end rounded-xl bg-ink px-5 py-3 font-bold text-white transition hover:-translate-y-0.5 hover:bg-coral">Search mock fares</button>
      {Object.values(errors)[0]?.message && <p role="alert" className="text-sm text-red-700 md:col-span-2 lg:col-span-4">{Object.values(errors)[0]?.message}</p>}
    </form>
  );
}
