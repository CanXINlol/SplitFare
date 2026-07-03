"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { searchSchema, type SearchInput } from "@/lib/schema";
import { Cabin, SortOption } from "@/lib/types";

const fieldClass = "mt-2 w-full rounded-xl border border-ink/15 bg-white px-4 py-3 outline-none transition focus:border-ink focus:ring-2 focus:ring-mint";

export function SearchForm() {
  const router = useRouter();
  const { register, handleSubmit, formState: { errors } } = useForm<SearchInput>({
    resolver: zodResolver(searchSchema),
    defaultValues: {
      origin: "MEL", destination: "PVG", departureDate: "2026-08-12",
      minGapHours: 3, maxGapHours: 12, passengers: 1, cabin: Cabin.Economy,
      maxResults: 20, sort: SortOption.Value,
      checkedBaggageLikelyRequired: false, visaTransitRequirementUnknown: true,
      currency: "AUD", promoCodeNote: "", memberPriceNote: "",
    },
  });
  const submit = (input: SearchInput) => router.push(`/results?${new URLSearchParams(Object.entries(input).map(([key, value]) => [key, String(value)]))}`);

  return (
    <form onSubmit={handleSubmit(submit)} className="grid gap-5 rounded-3xl bg-white/90 p-5 shadow-card md:grid-cols-2 lg:grid-cols-4 lg:p-7">
      <label className="text-sm font-bold">From<input aria-label="Origin" className={fieldClass} maxLength={3} {...register("origin")} /></label>
      <label className="text-sm font-bold">To<input aria-label="Destination" className={fieldClass} maxLength={3} {...register("destination")} /></label>
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
