"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useCityCatalog } from "@/lib/city-catalog";
import { useI18n } from "@/lib/i18n";
import type { City } from "@/lib/types";

export function CitySelector({ open, kind, value, excludedCityId, onSelect, onClose }: {
  open: boolean; kind: "from" | "to"; value: string; excludedCityId: string;
  onSelect: (city: City) => void; onClose: () => void;
}) {
  const { catalog } = useCityCatalog();
  const { locale, t } = useI18n();
  const selected = catalog?.cities.find((city) => city.cityId === value);
  const selectedCountry = catalog?.countries.find((country) => country.countryId === selected?.countryId);
  const [continentId, setContinentId] = useState(selectedCountry?.continentId ?? "asia");
  const [countryId, setCountryId] = useState(selectedCountry?.countryId ?? "china");
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    if (selectedCountry) { setContinentId(selectedCountry.continentId); setCountryId(selectedCountry.countryId); }
    closeRef.current?.focus();
    const keydown = (event: KeyboardEvent) => { if (event.key === "Escape") onClose(); };
    document.addEventListener("keydown", keydown);
    document.body.style.overflow = "hidden";
    return () => { document.removeEventListener("keydown", keydown); document.body.style.overflow = ""; };
  }, [open, onClose, selectedCountry]);

  const countries = useMemo(() => (catalog?.countries ?? []).filter((item) => item.continentId === continentId), [catalog, continentId]);
  const cities = useMemo(() => (catalog?.cities ?? []).filter((item) => item.countryId === countryId), [catalog, countryId]);
  if (!open || !catalog) return null;

  const switchContinent = (next: string) => {
    setContinentId(next);
    const first = catalog.countries.find((item) => item.continentId === next);
    if (first) setCountryId(first.countryId);
  };

  return <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
    <section className="city-dialog" role="dialog" aria-modal="true" aria-labelledby={`city-title-${kind}`}>
      <div className="dialog-head">
        <div><span className="eyebrow">{t(`search.${kind}`)}</span><h2 id={`city-title-${kind}`}>{t(`city.title.${kind}`)}</h2></div>
        <button ref={closeRef} className="icon-button" type="button" onClick={onClose} aria-label={t("city.close")}>×</button>
      </div>
      <div className="city-columns">
        <section><h3>{t("city.continent")}</h3><div className="selector-list">
          {catalog.continents.map((item) => <button type="button" key={item.continentId} className={continentId === item.continentId ? "active" : ""} onClick={() => switchContinent(item.continentId)}>{locale === "zh" ? item.continentNameZh : item.continentNameEn}</button>)}
        </div></section>
        <section><h3>{t("city.country")}</h3><div className="selector-list">
          {countries.map((item) => <button type="button" key={item.countryId} className={countryId === item.countryId ? "active" : ""} onClick={() => setCountryId(item.countryId)}>{locale === "zh" ? item.countryNameZh : item.countryNameEn}<small>{item.countryCode}</small></button>)}
        </div></section>
        <section className="city-list-panel"><h3>{t("city.city")}</h3><div className="city-grid">
          {cities.map((city) => {
            const disabled = !city.enabled || city.airportCodes.length === 0 || city.cityId === excludedCityId;
            return <button type="button" key={city.cityId} disabled={disabled} aria-pressed={city.cityId === value} className={city.cityId === value ? "selected" : ""} onClick={() => { onSelect(city); onClose(); }}>
              <strong>{locale === "zh" ? city.cityNameZh : city.cityNameEn}</strong>
              <span>{disabled && city.cityId !== excludedCityId ? t("city.unavailable") : `${t("city.airports")}: ${city.airportCodes.join(" · ")}`}</span>
            </button>;
          })}
        </div></section>
      </div>
      <div className="dialog-actions"><button type="button" className="button-secondary" onClick={onClose}>{t("city.cancel")}</button></div>
    </section>
  </div>;
}
