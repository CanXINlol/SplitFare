import { ItineraryType, type Itinerary, type Segment } from "@/lib/types";
import { clock, duration, money } from "@/lib/utils";

const riskStyle = { low: "bg-emerald-100 text-emerald-800", medium: "bg-amber-100 text-amber-800", high: "bg-orange-100 text-orange-800", extreme: "bg-red-100 text-red-800" };

export function ItineraryCard({ itinerary, label }: { itinerary: Itinerary; label?: string }) {
  const offerFor = (segment: Segment) => itinerary.offers.find(
    (offer) => offer.segments.some((offerSegment) => offerSegment.id === segment.id),
  );
  const freshness = itinerary.priceFreshness ?? {
    lastCheckedAt: itinerary.lastCheckedAt,
    expiresAt: itinerary.expiresAt,
    isExpired: new Date(itinerary.expiresAt).getTime() <= Date.now(),
  };
  return (
    <article className="rounded-3xl border border-ink/10 bg-white p-5 shadow-card md:p-7">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>{label && <p className="mb-2 text-xs font-black uppercase tracking-widest text-coral">{label}</p>}<p className="text-sm font-bold text-ink/55">{itinerary.type === ItineraryType.SplitTicket ? "Self-transfer · separate tickets" : "Protected itinerary"}</p><h2 className="mt-1 text-3xl font-black">{money(itinerary.totalPrice, itinerary.currency)}</h2><p className="mt-1 text-sm text-emerald-700">{itinerary.savingsVsBaseline === null ? "No protected baseline" : `Save ${money(itinerary.savingsVsBaseline, itinerary.currency)} vs baseline`} · Value {itinerary.valueScore}</p></div>
        <span className={`rounded-full px-3 py-1 text-xs font-black uppercase ${riskStyle[itinerary.riskLevel]}`}>{itinerary.riskLevel} risk · {itinerary.riskScore}</span>
      </div>
      <div className="my-6 grid gap-4 border-y border-ink/10 py-5 sm:grid-cols-3">
        <div><p className="text-xs uppercase text-ink/45">Route</p><p className="mt-1 font-bold">{itinerary.segments.map((segment, index) => <span key={segment.id}>{index > 0 && " → "}{segment.origin}{index === itinerary.segments.length - 1 && ` → ${segment.destination}`}</span>)}</p></div>
        <div><p className="text-xs uppercase text-ink/45">Connection gap</p><p className="mt-1 font-bold">{duration(itinerary.layoverGapMinutes)}{itinerary.layoverAirport && ` at ${itinerary.layoverAirport}`}</p></div>
        <div><p className="text-xs uppercase text-ink/45">Total duration</p><p className="mt-1 font-bold">{duration(itinerary.totalDurationMinutes)}</p></div>
      </div>
      <div className="space-y-3">{itinerary.segments.map((segment) => { const offer = offerFor(segment); return <div key={segment.id} className="flex flex-wrap justify-between gap-2 text-sm"><span className="font-bold">{clock(segment.departureAt)} {segment.origin} → {clock(segment.arrivalAt)} {segment.destination}</span><span className="text-ink/55">{segment.flightNumber} · {offer?.supplier ?? "Unknown supplier"} · baggage {offer?.baggageIncluded === true ? "included" : offer?.baggageIncluded === false ? "not included" : "unknown"}</span></div>; })}</div>
      {itinerary.warnings.length > 0 && <div className="mt-5 rounded-2xl border border-orange-200 bg-orange-50 p-4 text-sm"><p className="font-black">{itinerary.type === ItineraryType.SplitTicket ? "Self-transfer warning" : "Risk notes"}</p><ul className="mt-2 list-disc space-y-1 pl-5 leading-6">{itinerary.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul></div>}
      <p className="mt-4 text-xs text-ink/45">Price freshness: {freshness.isExpired ? "expired" : "fresh"} 路 Checked {new Date(freshness.lastCheckedAt).toLocaleString("en-AU", { timeZone: "UTC" })} UTC 路 Expires {new Date(freshness.expiresAt).toLocaleString("en-AU", { timeZone: "UTC" })} UTC</p>
      <p className="mt-4 text-xs text-ink/45">Suppliers: {itinerary.suppliers.join(", ")} · Mock checked {new Date(itinerary.lastCheckedAt).toLocaleString("en-AU", { timeZone: "UTC" })} UTC · Expires {new Date(itinerary.expiresAt).toLocaleString("en-AU", { timeZone: "UTC" })} UTC</p>
    </article>
  );
}
