"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { searchFlights } from "@/lib/api";
import { searchSchema } from "@/lib/schema";
import { ItineraryType, type Itinerary, type SearchResponse } from "@/lib/types";
import { ItineraryCard } from "./itinerary-card";

function cheapest(itineraries: Itinerary[]): Itinerary | null {
  return [...itineraries].sort((a, b) => a.totalPrice - b.totalPrice || a.riskScore - b.riskScore)[0] ?? null;
}

function longLayoverButCheaper(itineraries: Itinerary[]): Itinerary | null {
  return [...itineraries]
    .filter((itinerary) => itinerary.type === ItineraryType.SplitTicket)
    .filter((itinerary) => (itinerary.layoverGapMinutes ?? 0) >= 480)
    .filter((itinerary) => (itinerary.savingsVsBaseline ?? 0) > 0)
    .sort((a, b) => (b.savingsVsBaseline ?? 0) - (a.savingsVsBaseline ?? 0))[0] ?? null;
}

function availableGroups(groups: { title: string; subtitle: string; itinerary: Itinerary | null }[]) {
  return groups.filter((group): group is { title: string; subtitle: string; itinerary: Itinerary } => Boolean(group.itinerary));
}

export function ResultsView() {
  const params = useSearchParams();
  const [data, setData] = useState<SearchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    const parsed = searchSchema.safeParse(Object.fromEntries(params.entries()));
    if (!parsed.success) {
      setError("Invalid search parameters. Please return and try again.");
      return () => controller.abort();
    }
    searchFlights(parsed.data, controller.signal).then(setData).catch((reason: unknown) => {
      if (reason instanceof Error && reason.name !== "AbortError") setError(reason.message);
    });
    return () => controller.abort();
  }, [params]);

  if (error) return <div className="rounded-3xl bg-red-50 p-8"><p className="font-bold text-red-800">{error}</p><Link href="/" className="mt-4 inline-block underline">Back to search</Link></div>;
  if (!data) return <div className="py-24 text-center"><p className="animate-pulse font-bold">Combining fares...</p></div>;

  const groups = availableGroups([
    { title: "Best overall", subtitle: "Risk-adjusted value. Not guaranteed cheapest.", itinerary: data.ranked[0] ?? null },
    { title: "Cheapest", subtitle: "Lowest shown fare from connected/mock sources.", itinerary: cheapest(data.ranked) },
    { title: "Safest split-ticket", subtitle: "Lowest risk among separate-ticket options.", itinerary: data.safestSplit },
    { title: "Protected ticket", subtitle: "Single protected itinerary baseline.", itinerary: data.baseline },
    { title: "Long layover but cheaper", subtitle: "More waiting time in exchange for savings.", itinerary: longLayoverButCheaper(data.ranked) },
  ]);

  return (
    <>
      <section className="mb-6 rounded-3xl bg-ink p-5 text-white shadow-card md:p-7">
        <p className="text-xs font-black uppercase tracking-widest text-coral">Decision summary</p>
        <h1 className="mt-2 text-3xl font-black md:text-5xl">Pick the trade-off, not just the fare.</h1>
        <p className="mt-4 max-w-3xl text-sm leading-6 text-white/70">Separate-ticket options are clearly marked. Lower prices may mean self-transfer, baggage re-check, longer layovers, or less protection if a flight is delayed.</p>
      </section>
      <section className="grid gap-5">
        {groups.map((group) => <div key={group.title} className="scroll-mt-4"><div className="mb-3"><p className="text-xs font-black uppercase tracking-widest text-coral">{group.title}</p><p className="mt-1 text-sm text-ink/55">{group.subtitle}</p></div><ItineraryCard itinerary={group.itinerary} label={group.title} searchId={data.searchId} /></div>)}
      </section>
      <div className="mb-5 mt-14 flex items-end justify-between gap-4"><div><p className="text-xs font-black uppercase tracking-widest text-coral">Full ranking</p><h2 className="mt-2 text-3xl font-black">All itineraries</h2><p className="mt-2 text-sm text-ink/55">Sorted by selected value logic. High-risk options are not dressed up as recommendations.</p></div><span className="shrink-0 text-sm text-ink/50">{data.ranked.length} results</span></div>
      <div className="space-y-5">{data.ranked.map((itinerary, index) => <ItineraryCard key={itinerary.id} itinerary={itinerary} label={`Rank ${index + 1}`} searchId={data.searchId} />)}</div>
      <p className="mt-8 rounded-2xl bg-ink p-5 text-sm leading-6 text-white/75">{data.disclaimer} Prices must be re-verified before any future booking flow. No result is presented as guaranteed cheapest.</p>
    </>
  );
}
