"use client";

import { useEffect, useRef, useState } from "react";
import { verifyBookingOption } from "@/lib/api";
import { formatDateTime, formatMoney, formatTime } from "@/lib/format";
import { useI18n } from "@/lib/i18n";
import { ItineraryType, PriceStatus, VerificationStatus, type BookingOption, type Itinerary, type PreBookingVerificationResponse } from "@/lib/types";

const riskClass = { low: "risk-low", medium: "risk-medium", high: "risk-high", extreme: "risk-extreme" };

export function ItineraryCard({ itinerary, label, searchId, originCity, destinationCity }: {
  itinerary: Itinerary; label?: string; searchId: string; originCity: string; destinationCity: string;
}) {
  const { locale, t, warning } = useI18n();
  const [expanded, setExpanded] = useState(false);
  const [verifying, setVerifying] = useState<string | null>(null);
  const [verification, setVerification] = useState<PreBookingVerificationResponse | null>(null);
  const [verificationError, setVerificationError] = useState(false);
  const closeRef = useRef<HTMLButtonElement>(null);
  const split = itinerary.type === ItineraryType.SplitTicket;
  const first = itinerary.segments[0];
  const last = itinerary.segments.at(-1)!;
  const unknownBaggage = itinerary.offers.some((offer) => offer.baggageIncluded === null);
  const duration = (minutes: number | null) => minutes === null ? t("common.na") : t("common.minutes", { hours: Math.floor(minutes / 60), minutes: minutes % 60 });

  useEffect(() => {
    if (!verification && !verificationError) return;
    closeRef.current?.focus();
    const onKey = (event: KeyboardEvent) => { if (event.key === "Escape") { setVerification(null); setVerificationError(false); } };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [verification, verificationError]);

  const verify = async (option: BookingOption) => {
    setVerifying(option.id); setVerification(null); setVerificationError(false);
    try { setVerification(await verifyBookingOption({ searchId, itineraryId: itinerary.id, bookingOptionId: option.id })); }
    catch { setVerificationError(true); }
    finally { setVerifying(null); }
  };
  const primaryOption = itinerary.bookingOptions.find((option) => option.capabilities.supportsPriceVerify)
    ?? itinerary.bookingOptions.find((option) => option.url) ?? null;
  const priceLabel = (status: PriceStatus) => t(`price.${status}`);

  return <article className={`itinerary-card ${split ? "split-card" : "protected-card"}`}>
    <div className="card-accent" />
    <div className="card-top">
      <div className="card-route">
        <div className="card-tags">{label && <span className="feature-tag">{label}</span>}<span className={split ? "type-split" : "type-protected"}>{t(split ? "card.split" : "card.protected")}</span></div>
        <h3>{originCity} <em>({first.origin})</em><span>→</span>{destinationCity} <em>({last.destination})</em></h3>
        <div className="airport-route">{itinerary.segments.map((segment, index) => <span key={segment.id}>{index > 0 && <b>→</b>}{segment.originDisplay ?? segment.origin}{index === itinerary.segments.length - 1 && <><b>→</b>{segment.destinationDisplay ?? segment.destination}</>}</span>)}</div>
      </div>
      <div className="card-price"><small>{t("results.mock")}</small><strong>{formatMoney(itinerary.totalPrice, itinerary.currency, locale)}</strong><span className={(itinerary.savingsVsBaseline ?? 0) > 0 ? "saving-positive" : ""}>{(itinerary.savingsVsBaseline ?? 0) > 0 ? t("card.savings", { amount: formatMoney(itinerary.savingsVsBaseline!, itinerary.currency, locale) }) : t("card.noSavings")}</span></div>
    </div>
    <div className="card-facts">
      <div><small>{t("card.duration")}</small><strong>{duration(itinerary.totalDurationMinutes)}</strong></div>
      <div><small>{t("card.connection")}</small><strong>{itinerary.layoverAirport ? `${itinerary.layoverAirport} · ${duration(itinerary.layoverGapMinutes)}` : t("card.direct")}</strong></div>
      <div><small>{t("card.risk")}</small><strong className={`risk-pill ${riskClass[itinerary.riskLevel]}`}>{t(`risk.${itinerary.riskLevel}`)} · {itinerary.riskScore}</strong></div>
      <div><small>{t("card.source")}</small><strong>{itinerary.suppliers.join(" · ")}</strong></div>
    </div>
    {unknownBaggage && <span className="baggage-chip">{t("card.baggageUnknown")}</span>}
    {itinerary.warnings.length > 0 && <div className={`risk-box ${split ? "risk-box-visible" : ""}`}><strong>{t("risk.help")}</strong><ul>{itinerary.warnings.slice(0, split ? 3 : 1).map((item) => <li key={item}>{warning(item)}</li>)}</ul></div>}
    <div className="card-actions">
      <button type="button" className="button-secondary" onClick={() => setExpanded((value) => !value)}>{t(expanded ? "card.hideDetails" : "card.details")}</button>
      {primaryOption && <button type="button" className="button-primary compact" disabled={Boolean(verifying)} onClick={() => verify(primaryOption)}>{verifying ? t("verify.checking") : t(primaryOption.capabilities.supportsPriceVerify ? "card.verify" : "card.redirect")}</button>}
    </div>
    {expanded && <div className="card-details">
      <div className="segment-list">{itinerary.segments.map((segment, index) => <div className="segment" key={segment.id}><span className="ticket-number">{t("card.ticket", { count: split ? index + 1 : 1 })}</span><div><strong>{formatTime(segment.departureAt, locale)} {segment.origin} <span>→</span> {formatTime(segment.arrivalAt, locale)} {segment.destination}</strong><p>{segment.flightNumber} · {segment.airline} · {formatDateTime(segment.departureAt, locale)}</p></div></div>)}</div>
      <div className="booking-grid">{itinerary.bookingOptions.map((option) => {
        const actionable = option.capabilities.supportsPriceVerify || Boolean(option.url);
        return <button type="button" key={option.id} disabled={!actionable || Boolean(verifying)} onClick={() => verify(option)}><strong>{option.supplier ?? option.displayName ?? option.label}</strong><span>{option.priceAmount && option.currency ? `${formatMoney(option.priceAmount, option.currency, locale)} · ` : ""}{priceLabel(option.priceStatus)}</span><small>{t("price.change")}</small></button>;
      })}</div>
      <p className="freshness">{t("card.checked", { time: formatDateTime(itinerary.priceFreshness.lastCheckedAt, locale) })} · {t("price.change")}</p>
      {itinerary.warnings.length > 3 && <ul className="more-warnings">{itinerary.warnings.slice(3).map((item) => <li key={item}>{warning(item)}</li>)}</ul>}
    </div>}
    {(verification || verificationError) && <div className="modal-backdrop" role="presentation"><section className="verify-dialog" role="dialog" aria-modal="true" aria-labelledby={`verify-${itinerary.id}`}>
      <div className="dialog-head"><div><span className="eyebrow">PRE-BOOKING</span><h2 id={`verify-${itinerary.id}`}>{t("verify.title")}</h2></div><button ref={closeRef} className="icon-button" type="button" onClick={() => { setVerification(null); setVerificationError(false); }} aria-label={t("verify.close")}>×</button></div>
      {verificationError ? <div className="state-message error-state"><h3>{t("results.error")}</h3><p>{t("error.default")}</p></div> : verification && <>
        <div className={`verification-status ${verification.stillAvailable ? "available" : "unavailable"}`}><strong>{t(!verification.stillAvailable ? "verify.unavailable" : verification.status === VerificationStatus.Unsupported ? "verify.unsupported" : "verify.available")}</strong></div>
        {verification.previousPrice && verification.currency && <div className="price-comparison"><div><small>{t("verify.before")}</small><strong>{formatMoney(verification.previousPrice, verification.currency, locale)}</strong></div><span>→</span><div><small>{t("verify.now")}</small><strong>{verification.currentPrice ? formatMoney(verification.currentPrice, verification.currency, locale) : t("common.na")}</strong></div></div>}
        <p>{t(verification.priceChanged ? "verify.changed" : "verify.unchanged")}. {t("price.change")}</p>
        {!verification.bookingUrl && <p className="notice">{t("verify.noRedirect")}</p>}
      </>}
      <div className="dialog-actions"><button ref={closeRef} type="button" className="button-secondary" onClick={() => { setVerification(null); setVerificationError(false); }}>{t("verify.close")}</button>{verification && <button type="button" className="button-primary compact" disabled={!verification.canContinue || !verification.bookingUrl} onClick={() => { if (verification.bookingUrl) window.location.assign(verification.bookingUrl); }}>{t("verify.continue")}</button>}</div>
    </section></div>}
  </article>;
}
