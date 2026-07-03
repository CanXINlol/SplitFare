import { ItineraryType, PriceConfidence, type Itinerary, type Segment } from "@/lib/types";
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
  const bookingOptions = itinerary.bookingOptions ?? [];
  const coverage = itinerary.priceSourceCoverage;
  const optionNotes = bookingOptions
    .flatMap((option) => option.notes)
    .filter((note, index, notes) => notes.indexOf(note) === index)
    .slice(0, 5);
  const cta = bookingOptions.find((option) => option.url) ?? bookingOptions[0];
  const hasUnknownBaggage = itinerary.offers.some((offer) => offer.baggageIncluded === null);
  const urgentWarnings = itinerary.warnings.slice(0, 2);

  return (
    <article className="rounded-3xl border border-ink/10 bg-white p-5 shadow-card md:p-7">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          {label && <p className="mb-2 text-xs font-black uppercase tracking-widest text-coral">{label}</p>}
          <p className="text-sm font-bold text-ink/55">{itinerary.type === ItineraryType.SplitTicket ? "Self-transfer - separate tickets" : "Protected itinerary"}</p>
          <h2 className="mt-1 text-3xl font-black">{money(itinerary.totalPrice, itinerary.currency)}</h2>
          <p className="mt-1 text-sm text-emerald-700">{itinerary.savingsVsBaseline === null ? "No protected baseline" : `Save ${money(itinerary.savingsVsBaseline, itinerary.currency)} vs baseline`} - Value {itinerary.valueScore}</p>
        </div>
        <div className="flex max-w-full flex-col items-start gap-2 sm:items-end">
          <span className={`rounded-full px-3 py-1 text-xs font-black uppercase ${riskStyle[itinerary.riskLevel]}`}>{itinerary.riskLevel} risk - {itinerary.riskScore}</span>
          {cta && <a href={cta.url ?? "#"} target={cta.url ? "_blank" : undefined} rel={cta.url ? "noreferrer" : undefined} className={`rounded-xl bg-ink px-4 py-2 text-sm font-black text-white ${cta.url ? "transition hover:-translate-y-0.5 hover:bg-coral" : "pointer-events-none opacity-60"}`}>{cta.label}</a>}
        </div>
      </div>
      {urgentWarnings.length > 0 && <div className="mt-4 rounded-2xl border border-orange-200 bg-orange-50 p-4 text-sm"><p className="font-black">{itinerary.type === ItineraryType.SplitTicket ? "Self-transfer warning" : "Risk warning"}</p><ul className="mt-2 list-disc space-y-1 pl-5 leading-6">{urgentWarnings.map((warning) => <li key={warning}>{warning}</li>)}</ul></div>}
      <div className="my-6 grid gap-4 border-y border-ink/10 py-5 sm:grid-cols-3">
        <div><p className="text-xs uppercase text-ink/45">Route</p><p className="mt-1 font-bold">{itinerary.segments.map((segment, index) => <span key={segment.id}>{index > 0 && " → "}{segment.origin}{index === itinerary.segments.length - 1 && ` → ${segment.destination}`}</span>)}</p></div>
        <div><p className="text-xs uppercase text-ink/45">Connection gap</p><p className="mt-1 font-bold">{duration(itinerary.layoverGapMinutes)}{itinerary.layoverAirport && ` at ${itinerary.layoverAirport}`}</p></div>
        <div><p className="text-xs uppercase text-ink/45">Total duration</p><p className="mt-1 font-bold">{duration(itinerary.totalDurationMinutes)}</p></div>
      </div>
      <div className="mb-5 flex flex-wrap gap-2">{itinerary.suppliers.map((supplier) => <span key={supplier} className="rounded-full bg-mint px-3 py-1 text-xs font-black text-ink">{supplier}</span>)}{hasUnknownBaggage && <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-black text-amber-800">Baggage unknown</span>}{itinerary.type === ItineraryType.SplitTicket && <span className="rounded-full bg-orange-100 px-3 py-1 text-xs font-black text-orange-800">Separate tickets</span>}</div>
      <div className="space-y-3">{itinerary.segments.map((segment) => { const offer = offerFor(segment); return <div key={segment.id} className="flex flex-wrap justify-between gap-2 text-sm"><span className="font-bold">{clock(segment.departureAt)} {segment.origin} → {clock(segment.arrivalAt)} {segment.destination}</span><span className="text-ink/55">{segment.flightNumber} - {offer?.supplier ?? "Unknown supplier"} - baggage {offer?.baggageIncluded === true ? "included" : offer?.baggageIncluded === false ? "not included" : "unknown"}</span></div>; })}</div>
      {bookingOptions.length > 0 && <div className="mt-5 rounded-2xl border border-ink/10 bg-sand/60 p-4 text-sm"><div className="flex flex-wrap items-center justify-between gap-2"><p className="font-black">Booking options</p>{coverage && <p className="text-xs text-ink/50">Coverage: {coverage.confirmedSupplierCount} confirmed, {coverage.checkRequiredSupplierCount} check required, {coverage.unavailableSupplierCount} unavailable</p>}</div><div className="mt-3 grid gap-2 sm:grid-cols-2">{bookingOptions.map((option) => <a key={`${option.type}-${option.label}`} href={option.url ?? "#"} target={option.url ? "_blank" : undefined} rel={option.url ? "noreferrer" : undefined} aria-disabled={!option.url} className={`rounded-xl border border-ink/10 bg-white px-3 py-2 ${option.url ? "transition hover:-translate-y-0.5 hover:border-coral" : "cursor-not-allowed opacity-60"}`}><span className="block font-bold">{option.label}</span><span className="block text-xs text-ink/55">{option.priceConfidence === PriceConfidence.Confirmed && option.priceAmount && option.currency ? `${money(option.priceAmount, option.currency)} confirmed` : option.priceConfidence === PriceConfidence.CheckRequired ? "Check price on provider" : "Unavailable"}</span>{option.trackingId && <span className="block text-xs text-ink/40">tracking_id: {option.trackingId}</span>}</a>)}</div><p className="mt-3 text-xs text-ink/50">Price last checked {new Date(freshness.lastCheckedAt).toLocaleString("en-AU", { timeZone: "UTC" })} UTC. Price may change at checkout.</p>{optionNotes.length > 0 && <ul className="mt-2 list-disc space-y-1 pl-5 text-xs text-ink/55">{optionNotes.map((note) => <li key={note}>{note}</li>)}</ul>}</div>}
      {itinerary.warnings.length > urgentWarnings.length && <div className="mt-5 rounded-2xl border border-orange-200 bg-orange-50 p-4 text-sm"><p className="font-black">More risk notes</p><ul className="mt-2 list-disc space-y-1 pl-5 leading-6">{itinerary.warnings.slice(urgentWarnings.length).map((warning) => <li key={warning}>{warning}</li>)}</ul></div>}
      <p className="mt-4 text-xs text-ink/45">Price freshness: {freshness.isExpired ? "expired" : "fresh"} - Checked {new Date(freshness.lastCheckedAt).toLocaleString("en-AU", { timeZone: "UTC" })} UTC - Expires {new Date(freshness.expiresAt).toLocaleString("en-AU", { timeZone: "UTC" })} UTC</p>
      <p className="mt-4 text-xs text-ink/45">Suppliers: {itinerary.suppliers.join(", ")}</p>
    </article>
  );
}

