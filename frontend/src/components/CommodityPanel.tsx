import { useEffect, useState } from "react";
import { api } from "../api";
import type { Series, SeriesInfo } from "../types";

const pct = (value: number) => `${value >= 0 ? "+" : ""}${(value * 100).toFixed(2)}%`;
const month = (value: string) => new Date(`${value.slice(0, 7)}-01T12:00:00`).toLocaleDateString("pt-BR", { month: "short", year: "numeric" });

export function CommodityPanel({ factors }: { factors: SeriesInfo[] }) {
  const monthly = factors.filter((item) => item.frequency === "monthly");
  const [series, setSeries] = useState<Series[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!monthly.length) return;
    const controller = new AbortController();
    Promise.all(monthly.map((item) => api.series(item.series_id, controller.signal)))
      .then(setSeries)
      .catch((reason: Error) => { if (reason.name !== "AbortError") setError(reason.message); });
    return () => controller.abort();
  }, [factors]);

  if (!monthly.length) return null;
  return <section id="commodities" className="panel commodity-panel">
    <div className="panel-header"><div><span className="section-kicker">07 / OUTRAS VARIÁVEIS</span><h2>Commodities em outra escala de tempo.</h2><p>Preços médios mensais em dólares do Banco Mundial. Brent diário da EIA está disponível na regressão acima.</p></div><span className="panel-tag">FREQUÊNCIA MENSAL</span></div>
    {error && <div className="empty">Não foi possível carregar as séries mensais: {error}</div>}
    <div className="commodity-grid">{series.map((item) => {
      const latest = item.observations[item.observations.length - 1];
      const previous = item.observations[item.observations.length - 2];
      if (!latest) return null;
      return <div className="commodity-card" key={item.series.series_id}>
        <span>{item.series.name}</span><strong>{new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 2 }).format(latest.value)}</strong>
        <small>{item.series.unit} · {month(latest.date)}</small>
        <div><b>{previous ? pct(latest.value / previous.value - 1) : "—"}</b><span>vs. mês anterior</span></div>
      </div>;
    })}</div>
    <p className="method-inline">O mês identifica o período da média, não a data em que o dado se tornou público. Essas séries não entram na regressão diária; não há preenchimento de dias ou uso antecipado de informação. <a href="https://www.worldbank.org/en/research/commodity-markets" target="_blank" rel="noreferrer">Fonte: Banco Mundial ↗</a></p>
  </section>;
}
