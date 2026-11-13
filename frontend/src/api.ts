import type { Catalog, CompanyNews, Events, LocalNewsImpact, Regression, Series } from "./types";

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
  localStatus: () => get<{ enabled: boolean }>("/api/local/status"),
  localImport: async (pricesCsv: string, actionsCsv: string) => {
    const response = await fetch(`${base}/api/local/equity/import`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ prices_csv: pricesCsv, actions_csv: actionsCsv }) });
    const data = await response.json();
    if (!response.ok) throw new Error(data?.detail?.message ?? "Não foi possível importar os arquivos.");
    return data as { ticker: string; price_count: number; action_count: number; rights: string };
  },
  localSeries: (ticker: string) => get<Series>(`/api/local/equity/${encodeURIComponent(ticker)}/series`),
  localRegression: (ticker: string, factors: string[]) => {
    const params = new URLSearchParams();
    factors.forEach((factor) => params.append("factor_ids", factor));
    return get<Regression>(`/api/local/equity/${encodeURIComponent(ticker)}/regression?${params}`);
  },
  companyNews: (ticker: string, signal?: AbortSignal) => get<CompanyNews>(`/api/company/news?ticker=${encodeURIComponent(ticker)}`, signal),
  localNewsImpact: (ticker: string, factors: string[]) => {
    const params = new URLSearchParams();
    factors.forEach((factor) => params.append("factor_ids", factor));
    return get<LocalNewsImpact>(`/api/local/equity/${encodeURIComponent(ticker)}/news-impact?${params}`);
  },
  localArticleImpact: async (ticker: string, factors: string[], articlesCsv: string) => {
    const response = await fetch(`${base}/api/local/equity/${encodeURIComponent(ticker)}/article-impact`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ articles_csv: articlesCsv, factor_ids: factors }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data?.detail?.message ?? "Não foi possível estudar as notícias.");
    return data as LocalNewsImpact;
  },
};
