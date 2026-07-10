"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { CitySelector } from "./city-selector";
import { useCityCatalog } from "@/lib/city-catalog";
import { useI18n } from "@/lib/i18n";
import { searchSchema, type SearchInput } from "@/lib/schema";
import { Cabin, SortOption } from "@/lib/types";

const SEARCH_STORAGE_KEY = "splitfare:search:v2";

export function SearchForm() {
  const router = useRouter();
  const { catalog, citiesById, loading: catalogLoading, error: catalogError } = useCityCatalog();
  const { locale, t } = useI18n();
  const [picker, setPicker] = useState<"from" | "to" | null>(null);
  const [navigating, setNavigating] = useState(false);
  const defaultDate = new Date(Date.now() + 33 * 86400000).toISOString().slice(0, 10);
  const { register, handleSubmit, reset, setValue, watch, formState: { errors } } = useForm<SearchInput>({
    resolver: zodResolver(searchSchema),
    defaultValues: {
      originCityId: "city:melbourne-au", destinationCityId: "city:shanghai-cn", departureDate: defaultDate,
      minGapHours: 3, maxGapHours: 12, passengers: 1, cabin: Cabin.Economy, maxResults: 20,
      sort: SortOption.Value, checkedBaggageLikelyRequired: false, visaTransitRequirementUnknown: true,
      currency: "AUD", promoCodeNote: "", memberPriceNote: "",
    },
  });
  const originCityId = watch("originCityId");
  const destinationCityId = watch("destinationCityId");

  useEffect(() => {
    window.sessionStorage.removeItem("splitfare:last-search");
    window.localStorage.removeItem("splitfare:last-search");
    const saved = window.sessionStorage.getItem(SEARCH_STORAGE_KEY);
    if (!saved) return;
    try {
      const parsed = searchSchema.safeParse(JSON.parse(saved));
      if (parsed.success) reset(parsed.data);
      else window.sessionStorage.removeItem(SEARCH_STORAGE_KEY);
    } catch { window.sessionStorage.removeItem(SEARCH_STORAGE_KEY); }
  }, [reset]);

  const closePicker = useCallback(() => setPicker(null), []);
  const cityLabel = (cityId: string) => {
    const city = citiesById.get(cityId);
    return city ? (locale === "zh" ? city.cityNameZh : city.cityNameEn) : t("search.chooseCity");
  };
  const submit = (input: SearchInput) => {
    if (navigating) return;
    setNavigating(true);
    window.sessionStorage.setItem(SEARCH_STORAGE_KEY, JSON.stringify(input));
    const entries = Object.entries(input).filter(([, value]) => value !== null && value !== undefined).map(([key, value]) => [key, String(value)] as [string, string]);
    router.push(`/results?${new URLSearchParams(entries)}`);
  };

  return <>
    <form className="search-panel" onSubmit={handleSubmit(submit)} noValidate>
      <input type="hidden" {...register("originCityId")} /><input type="hidden" {...register("destinationCityId")} />
      <div className="route-fields">
        <label><span>{t("search.from")}</span><button type="button" aria-label={`${t("search.from")}: ${cityLabel(originCityId)}`} className="city-field" onClick={() => setPicker("from")} disabled={!catalog}><strong>{cityLabel(originCityId)}</strong><small>{citiesById.get(originCityId)?.airportCodes.join(" · ")}</small></button></label>
        <span className="route-arrow" aria-hidden="true">→</span>
        <label><span>{t("search.to")}</span><button type="button" aria-label={`${t("search.to")}: ${cityLabel(destinationCityId)}`} className="city-field" onClick={() => setPicker("to")} disabled={!catalog}><strong>{cityLabel(destinationCityId)}</strong><small>{citiesById.get(destinationCityId)?.airportCodes.join(" · ")}</small></button></label>
      </div>
      {(errors.destinationCityId || errors.originCityId) && <p className="form-error">{t(errors.destinationCityId?.message ?? errors.originCityId?.message ?? "search.sameCity")}</p>}
      {catalogError && <p className="form-error">{t("search.catalogError")}</p>}
      <div className="search-grid">
        <label><span>{t("search.departure")}</span><input type="date" min={new Date().toISOString().slice(0, 10)} {...register("departureDate")} /></label>
        <label><span>{t("search.passengers")}</span><select {...register("passengers")}>{[1,2,3,4,5,6,7,8,9].map((n) => <option key={n} value={n}>{n}</option>)}</select></label>
        <label><span>{t("search.cabin")}</span><select {...register("cabin")}>{Object.values(Cabin).map((value) => <option key={value} value={value}>{t(`common.${value}`)}</option>)}</select></label>
        <label><span>{t("search.sort")}</span><select {...register("sort")}><option value={SortOption.Value}>{t("search.value")}</option><option value={SortOption.Cheapest}>{t("search.cheapest")}</option></select></label>
        <label><span>{t("search.minGap")}</span><div className="unit-field"><input type="number" min="1" max="24" {...register("minGapHours")} /><small>{t("search.hours")}</small></div></label>
        <label><span>{t("search.maxGap")}</span><div className="unit-field"><input type="number" min="1" max="36" {...register("maxGapHours")} /><small>{t("search.hours")}</small></div></label>
        <label className="check-field"><input type="checkbox" {...register("checkedBaggageLikelyRequired")} /><span>{t("search.baggage")}</span></label>
        <button className="button-primary" type="submit" disabled={navigating || catalogLoading || catalogError}>{navigating ? t("search.loading") : t("search.submit")}<span>→</span></button>
      </div>
    </form>
    <CitySelector open={picker === "from"} kind="from" value={originCityId} excludedCityId={destinationCityId} onSelect={(city) => setValue("originCityId", city.cityId, { shouldValidate: true })} onClose={closePicker} />
    <CitySelector open={picker === "to"} kind="to" value={destinationCityId} excludedCityId={originCityId} onSelect={(city) => setValue("destinationCityId", city.cityId, { shouldValidate: true })} onClose={closePicker} />
  </>;
}
