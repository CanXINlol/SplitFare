"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { searchFlights } from "@/lib/api";
import { searchSchema } from "@/lib/schema";
import { ItineraryType, type Itinerary, type SearchResponse } from "@/lib/types";
import { ItineraryCard } from "./itinerary-card";

function longLayoverButCheaper(itineraries: Itinerary[]): Itinerary | null {
  return [...itineraries]
    .filter((itinerary) => itinerary.type === ItineraryType.SplitTicket)
    .filter((itinerary) => (itinerary.layoverGapMinutes ?? 0) >= 480)
    .filter((itinerary) => (itinerary.savingsVsBaseline ?? 0) > 0)
    .sort((a, b) => (b.savingsVsBaseline ?? 0) - (a.savingsVsBaseline ?? 0))[0] ?? null;
}

function availableGroups(groups: { title: string; subtitle: string; itinerary: Itinerary | null }[]) {
  const merged = new Map<string, { title: string; subtitle: string; itinerary: Itinerary }>();
  for (const group of groups) {
    if (!group.itinerary) continue;
    const existing = merged.get(group.itinerary.id);
    if (existing) {
      existing.title = `${existing.title} · ${group.title}`;
      existing.subtitle = `${existing.subtitle} ${group.subtitle}`;
    } else {
      merged.set(group.itinerary.id, { ...group, itinerary: group.itinerary });
    }
  }
  return [...merged.values()];
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
  if (!data) return <div className="py-24 text-center" role="status"><p className="animate-pulse font-bold">Comparing airports, transfer hubs, and ticket combinations...</p><p className="mt-2 text-sm text-ink/55">City searches may check several airport pairs. Please keep this page open.</p></div>;

  const ranked = data.results.rankedResults;
  const groups = availableGroups([
    { title: "Best overall", subtitle: "Risk-adjusted value. Not guaranteed cheapest.", itinerary: ranked[0] ?? null },
    { title: "Cheapest", subtitle: "Lowest shown fare from currently connected sources.", itinerary: data.cheapest },
    { title: "Safest split-ticket", subtitle: "Lowest risk among separate-ticket options.", itinerary: data.safestSplit },
    { title: "Protected ticket", subtitle: "Single protected itinerary baseline.", itinerary: data.baseline },
    { title: "Long layover but cheaper", subtitle: "More waiting time in exchange for savings.", itinerary: longLayoverButCheaper(ranked) },
  ]);

  return (
    <>
      <section className="mb-6 rounded-3xl bg-ink p-5 text-white shadow-card md:p-7">
        <p className="text-xs font-black uppercase tracking-widest text-coral">Decision summary</p>
        <h1 className="mt-2 text-3xl font-black md:text-5xl">Pick the trade-off, not just the fare.</h1>
        <p className="mt-4 max-w-3xl text-sm leading-6 text-white/70">Separate-ticket options are clearly marked. Lower prices may mean self-transfer, baggage re-check, longer layovers, or less protection if a flight is delayed.</p>
        <div className="mt-5 flex flex-wrap gap-2 text-xs font-bold">
          {data.metadata.demoData && <span className="rounded-full bg-coral px-3 py-1 text-ink">Demo Data · not live fares</span>}
          <span className="rounded-full bg-white/10 px-3 py-1">From: {data.metadata.searchedOriginAirports.join(", ")}</span>
          <span className="rounded-full bg-white/10 px-3 py-1">To: {data.metadata.searchedDestinationAirports.join(", ")}</span>
          <span className="rounded-full bg-white/10 px-3 py-1">Hubs checked: {data.metadata.searchedHubs.join(", ") || "none"}</span>
        </div>
        {data.metadata.queryPlanTruncated && <p className="mt-3 text-xs text-white/70">The airport matrix was capped at {data.metadata.supplierQueryLimit} supplier queries. Excluded hubs: {data.metadata.excludedAirports.join(", ")}.</p>}
      </section>
      {data.status === "partial" && <section className="mb-5 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm"><p className="font-black">Partial results</p><p className="mt-1 text-ink/65">Some supplier queries failed or timed out. Available results are still shown.</p><ul className="mt-2 list-disc space-y-1 pl-5 text-xs text-ink/55">{data.errors.slice(0, 3).map((item) => <li key={`${item.supplier}-${item.code}-${item.origin}-${item.destination}`}>{item.supplier ?? "Supplier"}: {item.message}</li>)}</ul></section>}
      {ranked.length === 0 && (
        <section className="rounded-3xl border border-ink/10 bg-white p-8 shadow-card">
          <p className="text-xs font-black uppercase tracking-widest text-coral">No matching mock fares</p>
          <h2 className="mt-2 text-3xl font-black">No itinerary matched this search.</h2>
          <p className="mt-3 max-w-2xl text-sm leading-6 text-ink/60">
            {data.explanation || "Try another supported seed city, airport, date, or connection-gap range."}
          </p>
          {data.errors.length > 0 && (
            <ul className="mt-4 list-disc space-y-1 pl-5 text-sm text-ink/55">
              {data.errors.slice(0, 3).map((item) => <li key={`${item.code}-${item.origin}-${item.destination}`}>{item.message}</li>)}
            </ul>
          )}
          <Link href="/" className="mt-5 inline-block rounded-xl bg-ink px-4 py-2 text-sm font-black text-white">Back to search</Link>
        </section>
      )}
      <section className="grid gap-5">
        {groups.map((group) => <div key={group.title} className="scroll-mt-4"><div className="mb-3"><p className="text-xs font-black uppercase tracking-widest text-coral">{group.title}</p><p className="mt-1 text-sm text-ink/55">{group.subtitle}</p></div><ItineraryCard itinerary={group.itinerary} label={group.title} searchId={data.searchId} demoData={data.metadata.demoData} /></div>)}
      </section>
      <div className="mb-5 mt-14 flex items-end justify-between gap-4"><div><p className="text-xs font-black uppercase tracking-widest text-coral">Full ranking</p><h2 className="mt-2 text-3xl font-black">All itineraries</h2><p className="mt-2 text-sm text-ink/55">Sorted by selected value logic. High-risk options are not dressed up as recommendations.</p></div><span className="shrink-0 text-sm text-ink/50">{ranked.length} results</span></div>
      <div className="space-y-5">{ranked.map((itinerary, index) => <ItineraryCard key={itinerary.id} itinerary={itinerary} label={`Rank ${index + 1}`} searchId={data.searchId} demoData={data.metadata.demoData} />)}</div>
      <p className="mt-8 rounded-2xl bg-ink p-5 text-sm leading-6 text-white/75">{data.disclaimer} Prices must be re-verified before any future booking flow. No result is presented as guaranteed cheapest.</p>
    </>
  );
}
