"use client";

import { useEffect, useMemo, useState } from "react";
import { formatMoney } from "@/lib/format";
import { useCityCatalog } from "@/lib/city-catalog";
import { useI18n } from "@/lib/i18n";
import {
  calculateComparison, deleteComparison, emptyComparison, exportComparisons,
  loadComparisons, saveComparison, type ManualComparisonRecord,
} from "@/lib/manual-pricing";
import type { CandidateRoute, ProviderSearchLink } from "@/lib/types";

const riskClass = { low: "risk-low", medium: "risk-medium", high: "risk-high", extreme: "risk-extreme" };
const feeFields = ["baggageFee", "seatFee", "paymentFee", "groundTransferFee", "accommodationFee", "otherFee"] as const;

export function RouteCard({ route, rank }: { route: CandidateRoute; rank: number }) {
  const { locale, t } = useI18n();
  const { citiesById } = useCityCatalog();
  const [pendingLink, setPendingLink] = useState<ProviderSearchLink | null>(null);
  const [comparisonOpen, setComparisonOpen] = useState(false);
  const [comparison, setComparison] = useState<ManualComparisonRecord>(() => emptyComparison(route.id));
  const [saved, setSaved] = useState(false);
  const [inputError, setInputError] = useState<string | null>(null);
  const cityName = (id: string) => {
    const city = citiesById.get(id);
    return city ? (locale === "zh" ? city.cityNameZh : city.cityNameEn) : id;
  };

  useEffect(() => {
    const stored = loadComparisons(window.localStorage).find((item) => item.itineraryId === route.id);
    if (stored) setComparison(stored);
  }, [route.id]);

  const calculation = useMemo(() => {
    try { return { totals: calculateComparison(comparison), error: null }; }
    catch (error) { return { totals: null, error: error instanceof Error ? error.message : "invalid_amount" }; }
  }, [comparison]);
  const totals = calculation.totals;
  const visibleError = inputError ?? calculation.error;
  const updateEntry = (index: number, field: string, value: string) => {
    setSaved(false);
    setComparison((current) => ({
      ...current, updatedAt: new Date().toISOString(),
      entries: current.entries.map((entry, entryIndex) => entryIndex === index ? { ...entry, [field]: value } : entry),
    }));
  };
  const updateCurrency = (currency: string) => setComparison((current) => ({
    ...current, currency, entries: current.entries.map((entry) => ({ ...entry, currency })),
  }));
  const save = () => {
    try { saveComparison(window.localStorage, comparison); setInputError(null); setSaved(true); }
    catch (error) { setInputError(error instanceof Error ? error.message : "invalid_amount"); }
  };
  const reset = () => {
    deleteComparison(window.localStorage, route.id);
    setComparison(emptyComparison(route.id, comparison.currency)); setSaved(false); setInputError(null);
  };
  const exportJson = () => {
    const blob = new Blob([exportComparisons(window.localStorage)], { type: "application/json" });
    const url = URL.createObjectURL(blob); const anchor = document.createElement("a");
    anchor.href = url; anchor.download = "splitfare-manual-comparisons.json"; anchor.click(); URL.revokeObjectURL(url);
  };
  const showLinks = (title: string, links: ProviderSearchLink[]) => <div className="provider-leg"><strong>{title}</strong><div>{links.map((link) => <button type="button" key={link.id} disabled={!link.searchUrl} onClick={() => setPendingLink(link)}>{link.providerDisplayName}<small>{t(link.linkType === "flight_search" ? "route.prefilled" : "route.manualSearch")}</small></button>)}</div></div>;

  return <article className="route-card">
    <div className="route-rank">#{rank}</div>
    <div className="route-card-head"><div><span className="type-split">{t("route.candidate")}</span><h2>{cityName(route.originCityId)} <em>({route.originAirport})</em> <span>→</span> {cityName(route.hubCityId)} <em>({route.hubArrivalAirport}{route.crossAirport ? ` → ${route.hubDepartureAirport}` : ""})</em> <span>→</span> {cityName(route.destinationCityId)} <em>({route.destinationAirport})</em></h2></div><strong className={`risk-pill ${riskClass[route.risk.level]}`}>{t(`risk.${route.risk.level}`)} · {route.risk.structuralScore}</strong></div>
    <div className="route-metrics"><div><small>{t("route.suggestedGap")}</small><strong>{route.suggestedMinGapHours}–{route.suggestedMaxGapHours} {t("search.hours")}</strong></div><div><small>{t("route.detour")}</small><strong>{t(`route.detour.${route.detourLevel}`)} · {route.detourRatio.toFixed(2)}×</strong></div><div><small>{t("route.transfer")}</small><strong>{t(route.crossAirport ? "route.crossAirport" : "route.sameAirport")}</strong></div><div><small>{t("route.tickets")}</small><strong>{t("route.separateTickets", { count: route.separateTicketCount })}</strong></div></div>
    <div className="route-reasons"><strong>{t("route.why")}</strong>{route.recommendationReasons.map((reason) => <span key={reason}>{t(`route.reason.${reason}`)}</span>)}</div>
    <div className="risk-box risk-box-visible"><strong>{t("route.structuralRisk")}</strong><ul>{[...route.risk.structuralWarnings, ...route.risk.unknownWarnings].map((warning) => <li key={warning}>{t(`route.warning.${warning}`)}</li>)}</ul><strong>{t("route.scheduleRisk")}</strong><ul>{route.risk.scheduleDependentWarnings.map((warning) => <li key={warning}>{t(`route.warning.${warning}`)}</li>)}</ul></div>
    <div className="provider-links">{showLinks(t("route.firstLeg", { origin: route.originAirport, destination: route.hubArrivalAirport }), route.firstLegLinks)}{showLinks(t("route.secondLeg", { origin: route.hubDepartureAirport, destination: route.destinationAirport }), route.secondLegLinks)}{route.fullRouteLinks.length > 0 && showLinks(t("route.fullRoute"), route.fullRouteLinks)}</div>
    <p className="route-price-note">{t("route.noLivePrices")}</p>
    <div className="card-actions"><button type="button" className="button-secondary" onClick={() => setComparisonOpen((value) => !value)}>{t(comparisonOpen ? "manual.hide" : "manual.open")}</button></div>
    {comparisonOpen && <section className="manual-workspace"><div className="manual-head"><div><span className="eyebrow">{t("manual.eyebrow")}</span><h3>{t("manual.title")}</h3><p>{t("manual.userEntered")}</p></div><label>{t("manual.currency")}<select value={comparison.currency} onChange={(event) => updateCurrency(event.target.value)}>{["AUD", "USD", "CNY", "GBP", "EUR"].map((currency) => <option key={currency}>{currency}</option>)}</select></label></div>
      <div className="manual-grid"><label>{t("manual.leg1")}<input inputMode="decimal" value={comparison.entries[0].amount} onChange={(event) => updateEntry(0, "amount", event.target.value)} placeholder="0.00" /></label><label>{t("manual.leg2")}<input inputMode="decimal" value={comparison.entries[1].amount} onChange={(event) => updateEntry(1, "amount", event.target.value)} placeholder="0.00" /></label>{feeFields.map((field) => <label key={field}>{t(`manual.${field}`)}<input inputMode="decimal" value={comparison.entries[0][field]} onChange={(event) => updateEntry(0, field, event.target.value)} placeholder="0.00" /></label>)}<label>{t("manual.protectedPrice")}<input inputMode="decimal" value={comparison.protectedTicketPrice} onChange={(event) => setComparison((current) => ({ ...current, protectedTicketPrice: event.target.value, updatedAt: new Date().toISOString() }))} placeholder="0.00" /></label><label>{t("manual.sourceNote")}<input value={comparison.entries[0].sourceNote} onChange={(event) => updateEntry(0, "sourceNote", event.target.value)} /></label></div>
      {visibleError && <p className="form-error">{t(`manual.error.${visibleError}`)}</p>}
      {totals && <div className="cost-summary"><div><small>{t("manual.segmentTotal")}</small><strong>{formatMoney(totals.segmentTotalMinor / 100, comparison.currency, locale)}</strong></div><div><small>{t("manual.feeTotal")}</small><strong>{formatMoney(totals.feeTotalMinor / 100, comparison.currency, locale)}</strong></div><div><small>{t("manual.totalCost")}</small><strong>{formatMoney(totals.splitTotalMinor / 100, comparison.currency, locale)}</strong></div>{totals.differenceMinor !== null && <div><small>{t(totals.differenceMinor >= 0 ? "manual.savings" : "manual.extraCost")}</small><strong>{formatMoney(Math.abs(totals.differenceMinor) / 100, comparison.currency, locale)}</strong></div>}</div>}
      {totals && <p className="decision-note">{t(`manual.decision.${totals.decisionCode}`)}</p>}
      {totals && totals.differenceMinor !== null && totals.differenceMinor > 0 && <p className="decision-note">{t("manual.riskTradeoff", { amount: formatMoney(totals.differenceMinor / 100, comparison.currency, locale), risk: route.risk.structuralScore })}</p>}
      <div className="manual-actions"><button type="button" className="button-primary compact" onClick={save}>{saved ? t("manual.saved") : t("manual.save")}</button><button type="button" className="button-secondary" onClick={reset}>{t("manual.reset")}</button><button type="button" className="button-secondary" onClick={exportJson}>{t("manual.export")}</button></div>
    </section>}
    {pendingLink && <div className="modal-backdrop" role="presentation"><section className="verify-dialog" role="dialog" aria-modal="true" aria-labelledby={`provider-${pendingLink.id}`}><div className="dialog-head"><div><span className="eyebrow">{t("route.providerReminder")}</span><h2 id={`provider-${pendingLink.id}`}>{pendingLink.providerDisplayName}</h2></div><button className="icon-button" type="button" onClick={() => setPendingLink(null)} aria-label={t("verify.close")}>×</button></div><p>{t("route.providerBody", { origin: pendingLink.originAirport, destination: pendingLink.destinationAirport, date: pendingLink.departureDate })}</p><p className="notice">{t("route.providerPrice")}</p><div className="dialog-actions"><button type="button" className="button-secondary" onClick={() => setPendingLink(null)}>{t("verify.close")}</button><a className="button-primary compact" href={pendingLink.searchUrl ?? undefined} target="_blank" rel="noopener noreferrer" onClick={() => setPendingLink(null)}>{t("route.openProvider")}</a></div></section></div>}
  </article>;
}
