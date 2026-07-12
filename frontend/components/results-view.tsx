"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { discoverRoutes } from "@/lib/api";
import { useCityCatalog } from "@/lib/city-catalog";
import { useI18n } from "@/lib/i18n";
import { clearComparisons } from "@/lib/manual-pricing";
import { searchSchema } from "@/lib/schema";
import { SearchStatus, type RouteDiscoveryResponse } from "@/lib/types";
import { RouteCard } from "./route-card";

export function ResultsView() {
  const params = useSearchParams();
  const query = params.toString();
  const { citiesById } = useCityCatalog();
  const { locale, t } = useI18n();
  const [data, setData] = useState<RouteDiscoveryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [storageEpoch, setStorageEpoch] = useState(0);
  const parsed = searchSchema.safeParse(Object.fromEntries(params.entries()));

  useEffect(() => {
    const controller = new AbortController();
    const input = searchSchema.safeParse(Object.fromEntries(new URLSearchParams(query).entries()));
    if (!input.success) { setError("validation_error"); return () => controller.abort(); }
    setData(null); setError(null);
    discoverRoutes(input.data, controller.signal).then(setData).catch((reason: unknown) => {
      if (reason instanceof Error && reason.name !== "AbortError") setError(reason.message);
    });
    return () => controller.abort();
  }, [query]);

  const cityName = (id: string | undefined) => {
    const city = id ? citiesById.get(id) : undefined;
    return city ? (locale === "zh" ? city.cityNameZh : city.cityNameEn) : "—";
  };
  const origin = cityName(parsed.success ? parsed.data.originCityId : undefined);
  const destination = cityName(parsed.success ? parsed.data.destinationCityId : undefined);

  if (error) return <section className="results-page"><div className="state-message error-state"><span>!</span><h1>{t("results.error")}</h1><p>{t(`error.${error}`) === `error.${error}` ? t("error.default") : t(`error.${error}`)}</p><Link href="/" className="button-primary">{t("results.back")}</Link></div></section>;
  if (!data) return <section className="results-page"><div className="state-message loading-state" role="status"><div className="loader"><i /><i /><i /></div><h1>{t("route.searching")}</h1><p>{t("route.searchingBody")}</p></div></section>;
  if (data.status === SearchStatus.Empty || data.routes.length === 0) return <section className="results-page"><div className="state-message empty-state"><span>○</span><h1>{t("route.empty")}</h1><p>{t("route.emptyBody")}</p><Link href="/" className="button-primary">{t("results.back")}</Link></div></section>;

  return <section className="results-page">
    <header className="results-head"><div><Link href="/" className="back-link">← {t("results.back")}</Link><span className="eyebrow">{t("route.discovery")}</span><h1>{origin} <span>→</span> {destination}</h1><p>{t("route.subtitle")}</p></div><div className="matrix-summary"><strong>{data.metadata.originAirports.join(" · ")}</strong><span>→</span><strong>{data.metadata.destinationAirports.join(" · ")}</strong><small>{t("route.count", { count: data.routes.length })}</small></div></header>
    <div className="route-disclaimer">{t("route.noLivePrices")}</div>
    <div className="section-title"><span className="eyebrow">{t("route.ranked")}</span><h2>{t("route.candidates")}</h2><p>{t("route.count", { count: data.routes.length })}</p></div>
    <div className="route-list">{data.routes.map((route, index) => <RouteCard key={`${route.id}-${storageEpoch}`} route={route} rank={index + 1} />)}</div>
    <div className="global-manual-actions"><button type="button" className="button-secondary" onClick={() => { clearComparisons(window.localStorage); setStorageEpoch((value) => value + 1); }}>{t("manual.clearAll")}</button></div>
    <p className="results-disclaimer">{t("route.disclaimer")}</p>
  </section>;
}
