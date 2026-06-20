"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { searchFlights } from "@/lib/api";
import { searchSchema } from "@/lib/schema";
import type { SearchResponse } from "@/lib/types";
import { ItineraryCard } from "./itinerary-card";

export function ResultsView() {
  const params = useSearchParams();
  const [data, setData] = useState<SearchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    const parsed = searchSchema.safeParse(Object.fromEntries(params.entries()));
    if (!parsed.success) { setError("Invalid search parameters. Please return and try again."); return controller.abort; }
    searchFlights(parsed.data, controller.signal).then(setData).catch((reason: unknown) => { if (reason instanceof Error && reason.name !== "AbortError") setError(reason.message); });
    return () => controller.abort();
  }, [params]);
  if (error) return <div className="rounded-3xl bg-red-50 p-8"><p className="font-bold text-red-800">{error}</p><Link href="/" className="mt-4 inline-block underline">Back to search</Link></div>;
  if (!data) return <div className="py-24 text-center"><p className="animate-pulse font-bold">Combining mock flights…</p></div>;
  return (
    <>
      <section className="grid gap-5 lg:grid-cols-3">{data.baseline && <ItineraryCard itinerary={data.baseline} label="Protected baseline" />}{data.cheapestSplit && <ItineraryCard itinerary={data.cheapestSplit} label="Cheapest split" />}{data.safestSplit && <ItineraryCard itinerary={data.safestSplit} label="Safest split" />}</section>
      <div className="mb-5 mt-14 flex items-end justify-between"><div><p className="text-xs font-black uppercase tracking-widest text-coral">Risk-adjusted ranking</p><h2 className="mt-2 text-3xl font-black">All mock itineraries</h2></div><span className="text-sm text-ink/50">{data.ranked.length} results</span></div>
      <div className="space-y-5">{data.ranked.map((itinerary, index) => <ItineraryCard key={itinerary.id} itinerary={itinerary} label={`Rank ${index + 1}`} />)}</div>
      <p className="mt-8 rounded-2xl bg-ink p-5 text-sm leading-6 text-white/75">{data.disclaimer} Prices must be re-verified before any future booking flow.</p>
    </>
  );
}
