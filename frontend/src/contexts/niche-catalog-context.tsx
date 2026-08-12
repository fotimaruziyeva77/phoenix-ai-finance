"use client";

import type { ReactNode } from "react";
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import type { NicheCatalogItemDto, NicheCatalogResponseDto } from "@/lib/api/niche-catalog";
import { fetchNicheCatalog } from "@/lib/api/niche-catalog";
import { setNicheCatalogCache } from "@/lib/bot-domain/niche-catalog-cache";
import { EMERGENCY_NICHE_CATALOG_ITEMS } from "@/lib/bot-domain/niche-emergency-fallback";

export type NicheCatalogStatus = "idle" | "loading" | "ready" | "error";

type NicheCatalogContextValue = {
  status: NicheCatalogStatus;
  schemaVersion: number | null;
  niches: NicheCatalogItemDto[];
  usingEmergencyFallback: boolean;
  refetch: () => Promise<void>;
};

const defaultValue: NicheCatalogContextValue = {
  status: "idle",
  schemaVersion: null,
  niches: [],
  usingEmergencyFallback: false,
  refetch: async () => {},
};

const NicheCatalogContext = createContext<NicheCatalogContextValue>(defaultValue);

type ProviderProps = {
  children: ReactNode;
  /** When passed, skips network (tests). */
  initialData?: NicheCatalogResponseDto;
};

export function NicheCatalogProvider({ children, initialData }: ProviderProps) {
  const [status, setStatus] = useState<NicheCatalogStatus>(() => (initialData ? "ready" : "loading"));
  const [schemaVersion, setSchemaVersion] = useState<number | null>(() => initialData?.schema_version ?? null);
  const [niches, setNiches] = useState<NicheCatalogItemDto[]>(() => initialData?.niches ?? []);
  const [usingEmergencyFallback, setUsingEmergencyFallback] = useState(false);

  const load = useCallback(async () => {
    setStatus("loading");
    setUsingEmergencyFallback(false);
    try {
      const data = await fetchNicheCatalog();
      setNicheCatalogCache(data);
      setSchemaVersion(data.schema_version);
      setNiches(data.niches);
      setStatus("ready");
    } catch {
      setNicheCatalogCache({
        schema_version: 1,
        niches: EMERGENCY_NICHE_CATALOG_ITEMS,
      });
      setSchemaVersion(1);
      setNiches(EMERGENCY_NICHE_CATALOG_ITEMS);
      setUsingEmergencyFallback(true);
      setStatus("error");
    }
  }, []);

  useEffect(() => {
    if (initialData) {
      setNicheCatalogCache(initialData);
      setSchemaVersion(initialData.schema_version);
      setNiches(initialData.niches);
      setStatus("ready");
      setUsingEmergencyFallback(false);
      return () => {
        setNicheCatalogCache(null);
      };
    }
    void load();
    return () => {
      setNicheCatalogCache(null);
    };
  }, [initialData, load]);

  const value = useMemo<NicheCatalogContextValue>(
    () => ({
      status,
      schemaVersion,
      niches,
      usingEmergencyFallback,
      refetch: load,
    }),
    [load, niches, schemaVersion, status, usingEmergencyFallback],
  );

  return <NicheCatalogContext.Provider value={value}>{children}</NicheCatalogContext.Provider>;
}

export function useNicheCatalog(): NicheCatalogContextValue {
  return useContext(NicheCatalogContext);
}
