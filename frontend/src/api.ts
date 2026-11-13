import type { Catalog, Events, Regression, Series } from "./types";

const base = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, "") ?? "";

async function get<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${base}${path}`, { signal });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail?.message ?? `Serviço indisponível (HTTP ${response.status}).`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  catalog: (signal?: AbortSignal) => get<Catalog>("/api/catalog", signal),
  series: (id: string, signal?: AbortSignal) => get<Series>(`/api/series/${encodeURIComponent(id)}`, signal),
  regression: (id: string, factors: string[], signal?: AbortSignal) => {
    const params = new URLSearchParams({ instrument_id: id });
    factors.forEach((factor) => params.append("factor_ids", factor));
    return get<Regression>(`/api/research/regression?${params}`, signal);
  },
  events: (id: string, benchmark: string, signal?: AbortSignal) => {
    const params = new URLSearchParams({ topic: "copom", instrument_id: id, benchmark_id: benchmark, limit: "12" });
    return get<Events>(`/api/events?${params}`, signal);
  },
};
