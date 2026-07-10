"use client";

import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { getCityCatalog } from "./api";
import type { City, CityCatalog } from "./types";

type CatalogState = { catalog: CityCatalog | null; citiesById: Map<string, City>; loading: boolean; error: boolean };
const CatalogContext = createContext<CatalogState | null>(null);

export function CityCatalogProvider({ children }: { children: ReactNode }) {
  const [catalog, setCatalog] = useState<CityCatalog | null>(null);
  const [error, setError] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    getCityCatalog(controller.signal).then((value) => { setCatalog(value); setError(false); }).catch((reason: unknown) => {
      if (reason instanceof DOMException && reason.name === "AbortError") return;
      setError(true);
    });
    return () => controller.abort();
  }, []);
  const value = useMemo(() => ({ catalog, citiesById: new Map((catalog?.cities ?? []).map((city) => [city.cityId, city])), loading: !catalog && !error, error }), [catalog, error]);
  return <CatalogContext.Provider value={value}>{children}</CatalogContext.Provider>;
}

export function useCityCatalog(): CatalogState {
  const value = useContext(CatalogContext);
  if (!value) throw new Error("useCityCatalog must be used inside CityCatalogProvider");
  return value;
}
