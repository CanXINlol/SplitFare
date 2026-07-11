"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { searchFlights } from "@/lib/api";
import { useCityCatalog } from "@/lib/city-catalog";
import { useI18n } from "@/lib/i18n";
import { searchSchema } from "@/lib/schema";
import { SearchStatus, type Itinerary, type SearchResponse } from "@/lib/types";
import { ItineraryCard } from "./itinerary-card";

export function ResultsView() {
  const params = useSearchParams();
  const query = params.toString();
  const { citiesById } = useCityCatalog();
  const { locale, t } = useI18n();
  const [data, setData] = useState<SearchResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const parsed = searchSchema.safeParse(Object.fromEntries(params.entries()));

  useEffect(() => {
    const controller = new AbortController();
    const input = searchSchema.safeParse(Object.fromEntries(new URLSearchParams(query).entries()));
    if (!input.success) { setError("validation_error"); return () => controller.abort(); }
    setData(null); setError(null);
    searchFlights(input.data, controller.signal).then(setData).catch((reason: unknown) => {
      if (reason instanceof Error && reason.name !== "AbortError") setError(reason.message);
    });
    return () => controller.abort();
  }, [query]);

  const cityName = (id: string | undefined) => {
    const city = id ? citiesById.get(id) : undefined;
    return city ? (locale === "zh" ? city.cityNameZh : city.cityNameEn) : "—";
  };
  const originId = parsed.success ? parsed.data.originCityId : undefined;
  const destinationId = parsed.success ? parsed.data.destinationCityId : undefined;
  const origin = cityName(originId); const destination = cityName(destinationId);

  if (error) return <section className="results-page"><div className="state-message error-state"><span>!</span><h1>{t("results.error")}</h1><p>{t(`error.${error}`) === `error.${error}` ? t("error.default") : t(`error.${error}`)}</p><Link href="/" className="button-primary">{t("results.back")}</Link></div></section>;
  if (!data) return <section className="results-page"><div className="state-message loading-state" role="status"><div className="loader"><i /><i /><i /></div><h1>{t("results.searching")}</h1><p>{t("results.searchingBody")}</p></div></section>;
  const ranked = data.results.rankedResults;
  if (data.status === SearchStatus.Failed) {
    const code = data.errors[0]?.code ?? "SUPPLIER_UNAVAILABLE";
    const translated = t(`error.${code}`);
    return <section className="results-page"><div className="state-message error-state"><span>!</span><h1>{t("results.error")}</h1><p>{translated === `error.${code}` ? t("results.supplierFailed") : translated}</p><Link href="/" className="button-primary">{t("results.back")}</Link></div></section>;
  }
  if (ranked.length === 0) return <section className="results-page"><div className="state-message empty-state"><span>○</span><h1>{t("results.empty")}</h1><p>{t("results.emptyBody")}</p><Link href="/" className="button-primary">{t("results.back")}</Link></div></section>;

  const featured: { key: string; itinerary: Itinerary | null }[] = [
    { key: "best", itinerary: ranked[0] ?? null }, { key: "cheapest", itinerary: data.cheapest },
    { key: "safest", itinerary: data.safestSplit }, { key: "baseline", itinerary: data.baseline },
  ];
  const uniqueFeatured = featured.filter((entry, index, list) => entry.itinerary && list.findIndex((other) => other.itinerary?.id === entry.itinerary?.id) === index);

  return <section className="results-page">
    <header className="results-head"><div><Link href="/" className="back-link">← {t("results.back")}</Link><span className="eyebrow">{t(`mode.${data.metadata.mode}`)}</span><h1>{origin} <span>→</span> {destination}</h1><p>{t("results.subtitle")}</p></div><div className="matrix-summary"><strong>{data.metadata.searchedOriginAirports.join(" · ")}</strong><span>→</span><strong>{data.metadata.searchedDestinationAirports.join(" · ")}</strong><small>{t("results.count", { count: ranked.length })}</small></div></header>
    {data.status === "partial" && <div className="partial-banner">{t("results.partial")}</div>}
    <div className="featured-grid">{uniqueFeatured.map(({ key, itinerary }) => itinerary && <ItineraryCard key={itinerary.id} itinerary={itinerary} label={t(`results.${key}`)} searchId={data.searchId} originCity={origin} destinationCity={destination} mode={data.metadata.mode} />)}</div>
    <div className="section-title"><span className="eyebrow">{t("results.ranked")}</span><h2>{t("results.all")}</h2><p>{t("results.count", { count: ranked.length })}</p></div>
    <div className="result-list">{ranked.map((itinerary, index) => <ItineraryCard key={itinerary.id} itinerary={itinerary} label={`#${index + 1}`} searchId={data.searchId} originCity={origin} destinationCity={destination} mode={data.metadata.mode} />)}</div>
    <p className="results-disclaimer">{t("disclaimer")}</p>
  </section>;
}
