"use client";

import { useState } from "react";
import { verifyBookingOption } from "@/lib/api";
import {
  BookingOptionType,
  ItineraryType,
  PriceConfidence,
  type BookingOption,
  type Itinerary,
  type PreBookingVerificationResponse,
  type Segment,
} from "@/lib/types";
import { clock, duration, money } from "@/lib/utils";

const riskStyle = { low: "bg-emerald-100 text-emerald-800", medium: "bg-amber-100 text-amber-800", high: "bg-orange-100 text-orange-800", extreme: "bg-red-100 text-red-800" };

export function ItineraryCard({ itinerary, label, searchId }: { itinerary: Itinerary; label?: string; searchId?: string }) {
  const [verification, setVerification] = useState<PreBookingVerificationResponse | null>(null);
  const [verificationError, setVerificationError] = useState<string | null>(null);
  const [verifyingKey, setVerifyingKey] = useState<string | null>(null);
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
  const offerForOption = (option: BookingOption) => itinerary.offers.find((offer) => option.supplier && offer.supplier === option.supplier) ?? itinerary.offers[0];

  const handleVerify = async (option: BookingOption) => {
    const optionKey = `${option.type}-${option.label}`;
    setVerifyingKey(optionKey);
    setVerificationError(null);
    setVerification(null);
    const linkedOffer = offerForOption(option);
    if (!linkedOffer) {
      setVerificationError("This itinerary has no offer to verify.");
      setVerifyingKey(null);
      return;
    }
    try {
      const result = await verifyBookingOption({
        searchId,
        itineraryId: itinerary.id,
        offerId: option.type === BookingOptionType.TripCom ? null : linkedOffer?.id,
        supplier: option.supplier ?? linkedOffer.supplier,
        bookingOptionType: option.type,
        bookingOptionLabel: option.label,
        previousPrice: option.priceAmount,
        currency: option.currency ?? itinerary.currency,
        bookingUrl: option.url,
        trackingId: option.trackingId,
      });
      setVerification(result);
    } catch (error) {
      setVerificationError(error instanceof Error ? error.message : "Could not verify this booking option.");
    } finally {
      setVerifyingKey(null);
    }
  };
  const closeVerification = () => {
    setVerification(null);
    setVerificationError(null);
  };

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
          {cta && <button type="button" onClick={() => handleVerify(cta)} disabled={!cta.url || verifyingKey !== null} className={`rounded-xl bg-ink px-4 py-2 text-sm font-black text-white ${cta.url ? "transition hover:-translate-y-0.5 hover:bg-coral" : "pointer-events-none opacity-60"}`}>{verifyingKey ? "Verifying..." : cta.label}</button>}
        </div>
      </div>
      {urgentWarnings.length > 0 && <div className="mt-4 rounded-2xl border border-orange-200 bg-orange-50 p-4 text-sm"><p className="font-black">{itinerary.type === ItineraryType.SplitTicket ? "Self-transfer warning" : "Risk warning"}</p><ul className="mt-2 list-disc space-y-1 pl-5 leading-6">{urgentWarnings.map((warning) => <li key={warning}>{warning}</li>)}</ul></div>}
      <div className="my-6 grid gap-4 border-y border-ink/10 py-5 sm:grid-cols-3">
        <div><p className="text-xs uppercase text-ink/45">Route</p><p className="mt-1 font-bold">{itinerary.segments.map((segment, index) => <span key={segment.id}>{index > 0 && " → "}{segment.origin}{index === itinerary.segments.length - 1 && ` → ${segment.destination}`}</span>)}</p></div>
        <div><p className="text-xs uppercase text-ink/45">Connection gap</p><p className="mt-1 font-bold">{duration(itinerary.layoverGapMinutes)}{itinerary.layoverAirport && ` at ${itinerary.layoverAirport}`}</p></div>
        <div><p className="text-xs uppercase text-ink/45">Total duration</p><p className="mt-1 font-bold">{duration(itinerary.totalDurationMinutes)}</p></div>
      </div>
      <div className="mb-5 flex flex-wrap gap-2">{itinerary.suppliers.map((supplier) => <span key={supplier} className="rounded-full bg-mint px-3 py-1 text-xs font-black text-ink">{supplier}</span>)}{hasUnknownBaggage && <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-black text-amber-800">Baggage unknown</span>}{itinerary.type === ItineraryType.SplitTicket && <span className="rounded-full bg-orange-100 px-3 py-1 text-xs font-black text-orange-800">Separate tickets</span>}</div>
      <div className="space-y-3">{itinerary.segments.map((segment) => { const offer = offerFor(segment); return <div key={segment.id} className="flex flex-wrap justify-between gap-2 text-sm"><span className="font-bold">{clock(segment.departureAt)} {segment.originDisplay ?? segment.origin} → {clock(segment.arrivalAt)} {segment.destinationDisplay ?? segment.destination}</span><span className="text-ink/55">{segment.flightNumber} - {offer?.supplier ?? "Unknown supplier"} - baggage {offer?.baggageIncluded === true ? "included" : offer?.baggageIncluded === false ? "not included" : "unknown"}</span></div>; })}</div>
      {bookingOptions.length > 0 && <div className="mt-5 rounded-2xl border border-ink/10 bg-sand/60 p-4 text-sm"><div className="flex flex-wrap items-center justify-between gap-2"><p className="font-black">Booking options</p>{coverage && <p className="text-xs text-ink/50">Coverage: {coverage.confirmedSupplierCount} confirmed, {coverage.checkRequiredSupplierCount} check required, {coverage.unavailableSupplierCount} unavailable</p>}</div><div className="mt-3 grid gap-2 sm:grid-cols-2">{bookingOptions.map((option) => { const key = `${option.type}-${option.label}`; return <button type="button" key={key} onClick={() => handleVerify(option)} disabled={!option.url || verifyingKey !== null} aria-disabled={!option.url || verifyingKey !== null} className={`rounded-xl border border-ink/10 bg-white px-3 py-2 text-left ${option.url ? "transition hover:-translate-y-0.5 hover:border-coral" : "cursor-not-allowed opacity-60"}`}><span className="block font-bold">{option.label}</span><span className="block text-xs text-ink/55">{option.priceConfidence === PriceConfidence.Confirmed && option.priceAmount && option.currency ? `${money(option.priceAmount, option.currency)} confirmed` : option.priceConfidence === PriceConfidence.CheckRequired ? "Check price on provider" : "Unavailable"}</span>{option.trackingId && <span className="block text-xs text-ink/40">tracking_id: {option.trackingId}</span>}{verifyingKey === key && <span className="mt-1 block text-xs font-bold text-coral">Verifying before redirect...</span>}</button>; })}</div><p className="mt-3 text-xs text-ink/50">Price last checked {new Date(freshness.lastCheckedAt).toLocaleString("en-AU", { timeZone: "UTC" })} UTC. Price may change at checkout.</p>{optionNotes.length > 0 && <ul className="mt-2 list-disc space-y-1 pl-5 text-xs text-ink/55">{optionNotes.map((note) => <li key={note}>{note}</li>)}</ul>}</div>}
      {itinerary.warnings.length > urgentWarnings.length && <div className="mt-5 rounded-2xl border border-orange-200 bg-orange-50 p-4 text-sm"><p className="font-black">More risk notes</p><ul className="mt-2 list-disc space-y-1 pl-5 leading-6">{itinerary.warnings.slice(urgentWarnings.length).map((warning) => <li key={warning}>{warning}</li>)}</ul></div>}
      <p className="mt-4 text-xs text-ink/45">Price freshness: {freshness.isExpired ? "expired" : "fresh"} - Checked {new Date(freshness.lastCheckedAt).toLocaleString("en-AU", { timeZone: "UTC" })} UTC - Expires {new Date(freshness.expiresAt).toLocaleString("en-AU", { timeZone: "UTC" })} UTC</p>
      <p className="mt-4 text-xs text-ink/45">Suppliers: {itinerary.suppliers.join(", ")}</p>
      {(verification || verificationError) && <div role="dialog" aria-modal="true" aria-label="Pre-booking verification" className="fixed inset-0 z-50 flex items-end bg-ink/45 p-4 sm:items-center sm:justify-center"><div className="w-full max-w-lg rounded-3xl bg-white p-5 shadow-card"><p className="text-xs font-black uppercase tracking-widest text-coral">Pre-booking verification</p>{verificationError ? <><h3 className="mt-2 text-2xl font-black">Could not verify this option</h3><p className="mt-3 text-sm text-ink/65">{verificationError}</p></> : verification && <><h3 className="mt-2 text-2xl font-black">{verification.stillAvailable ? "Review before leaving SplitFare" : "This option is not available"}</h3><p className="mt-3 text-sm text-ink/65">{verification.message}</p>{verification.priceChanged && verification.previousPrice && verification.currentPrice && verification.currency && <div className="mt-4 rounded-2xl bg-amber-50 p-4 text-sm"><p className="font-black">Price changed</p><p className="mt-1">Before: {money(verification.previousPrice, verification.currency)} → After: {money(verification.currentPrice, verification.currency)}</p></div>}{!verification.priceChanged && verification.currentPrice && verification.currency && <p className="mt-4 rounded-2xl bg-emerald-50 p-4 text-sm font-bold">Current verified price: {money(verification.currentPrice, verification.currency)}</p>}{verification.requiresPriceCheck && <p className="mt-4 rounded-2xl bg-sand p-4 text-sm">This provider link cannot confirm price inside SplitFare. Check the final price on the provider before booking.</p>}<p className="mt-4 text-xs text-ink/45">Checked {new Date(verification.checkedAt).toLocaleString("en-AU", { timeZone: "UTC" })} UTC. Prices may still change after redirect.</p></>}<div className="mt-5 flex flex-wrap justify-end gap-3"><button type="button" onClick={closeVerification} className="rounded-xl border border-ink/15 px-4 py-2 text-sm font-black">Cancel</button>{verification && <button type="button" disabled={!verification.canContinue || !verification.bookingUrl} onClick={() => { if (verification.bookingUrl) window.location.href = verification.bookingUrl; }} className={`rounded-xl px-4 py-2 text-sm font-black text-white ${verification.canContinue && verification.bookingUrl ? "bg-ink hover:bg-coral" : "bg-ink/30"}`}>{verification.canContinue ? "Continue to provider" : "Unavailable"}</button>}</div></div></div>}
    </article>
  );
}
