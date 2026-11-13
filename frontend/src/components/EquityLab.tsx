import { useEffect, useState } from "react";
import { api } from "../api";
import type { LocalNewsImpact, Regression, Series } from "../types";
import { ReturnChart } from "./ReturnChart";

const pct = (value: number) => `${(value * 100).toFixed(2)}%`;
const bp = (value: number) => `${(value * 10000).toFixed(2)} bp`;
const signed = (value: number | null) => value == null ? "—" : `${value > 0 ? "+" : ""}${pct(value)}`;
const dateLabel = (value: string) => new Date(`${value.slice(0, 10)}T12:00:00`).toLocaleDateString("pt-BR", { day: "2-digit", month: "short", year: "numeric" });

export function EquityLab({ factorIds }: { factorIds: string[] }) {
  const [enabled, setEnabled] = useState(false);
  const [checking, setChecking] = useState(true);
  const [pricesFile, setPricesFile] = useState<File | null>(null);
  const [actionsFile, setActionsFile] = useState<File | null>(null);
  const [ticker, setTicker] = useState("");
  const [series, setSeries] = useState<Series | null>(null);
  const [regression, setRegression] = useState<Regression | null>(null);
  const [impact, setImpact] = useState<LocalNewsImpact | null>(null);
  const [impactError, setImpactError] = useState<string | null>(null);
  const [selectedImpact, setSelectedImpact] = useState<string | null>(null);
  const [impactHorizon, setImpactHorizon] = useState<1 | 3 | 5>(3);
  const [mode, setMode] = useState<"price" | "total">("total");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => { api.localStatus().then((value) => setEnabled(value.enabled)).catch(() => setEnabled(false)).finally(() => setChecking(false)); }, []);

  async function importFiles() {
    if (!pricesFile || !actionsFile) return;
    setBusy(true);
    setError(null);
    setImpact(null);
    setImpactError(null);
    try {
      const result = await api.localImport(await pricesFile.text(), await actionsFile.text());
      setTicker(result.ticker);
      const nextSeries = await api.localSeries(result.ticker);
      setSeries(nextSeries);
      if (nextSeries.cash_flows.length === 0) {
        setRegression(null);
        setError("Não há dividendos ou JCP completos para a comparação. Os preços foram importados, mas o ajuste não pode ser calculado.");
      } else {
        setRegression(await api.localRegression(result.ticker, factorIds));
      }
      try {
        const nextImpact = await api.localNewsImpact(result.ticker, factorIds);
        setImpact(nextImpact);
        setSelectedImpact(nextImpact.events.find((item) => item.windows["3"]?.available)?.filing_id ?? nextImpact.events[0]?.filing_id ?? null);
      } catch (reason) {
        setImpactError(reason instanceof Error ? reason.message : "O estudo de documentos não está disponível.");
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Não foi possível concluir a importação.");
    } finally { setBusy(false); }
  }

  const activeImpact = impact?.events.find((item) => item.filing_id === selectedImpact) ?? impact?.events[0];
  const window = activeImpact?.windows[String(impactHorizon)];
  const cohort = impact?.cohort[String(impactHorizon)];

  return <section id="acoes" className="panel equity-panel"><div className="panel-header"><div><span className="section-kicker">06 / AÇÕES & PROVENTOS</span><h2>Repita o estudo com uma ação.</h2><p>Preços e eventos importados pelo pesquisador ficam somente no banco local.</p></div><span className="panel-tag">PESQUISA LOCAL</span></div>
    {checking ? <p className="equity-note">Verificando a pesquisa local…</p> : !enabled ? <div className="equity-disabled"><strong>Disponível na execução local do projeto.</strong><p>A demonstração pública não recebe arquivos de preços de ações. Ao executar o projeto no seu computador, ative a importação local e use seus próprios CSVs.</p><a href="https://github.com/MolinaGG/market-lens-br#executar-localmente" target="_blank" rel="noreferrer">Ver instruções no projeto ↗</a></div> : <>
      <div className="equity-import"><label><span>1 · PREÇOS DIÁRIOS</span><input type="file" accept=".csv,text/csv" onChange={(event) => setPricesFile(event.target.files?.[0] ?? null)} /><small>Colunas: ticker, date, close</small></label><label><span>2 · DESDOBRAMENTOS E PROVENTOS</span><input type="file" accept=".csv,text/csv" onChange={(event) => setActionsFile(event.target.files?.[0] ?? null)} /><small>ticker, ex_date, kind, amount, split_factor</small></label><button type="button" disabled={busy || !pricesFile || !actionsFile} onClick={importFiles}>{busy ? "Analisando…" : "Importar e comparar →"}</button></div>
      <p className="equity-note">Datas em AAAA-MM-DD; `kind` aceita dividend, jcp e split. Valor é por ação na data ex. O servidor público bloqueia esta operação.</p>
      {error && <div className="equity-error" role="alert">{error}</div>}
      {series && <p className="equity-note">{ticker}: {series.observations.length} preços e {series.cash_flows.length} proventos validados.</p>}
      {series && regression && <div className="equity-result"><div className="equity-result-head"><strong>{ticker} · comparação de retornos</strong><div className="mode-switch" role="group" aria-label="Retorno da ação destacado"><button type="button" className={mode === "price" ? "selected" : ""} aria-pressed={mode === "price"} onClick={() => setMode("price")}>Só preço</button><button type="button" className={mode === "total" ? "selected" : ""} aria-pressed={mode === "total"} onClick={() => setMode("total")}>Com proventos</button></div></div><ReturnChart points={regression.points} couponDates={series.cash_flows.map((flow) => flow.date)} mode={mode} cashLabel="proventos" /><div className="equity-comparison"><div><span>SEM PROVENTOS</span><strong>R² {pct(regression.price.r_squared)}</strong><small>Erro futuro {bp(regression.price.holdout_rmse)}</small></div><div><span>COM PROVENTOS</span><strong>R² {pct(regression.total.r_squared)}</strong><small>Erro futuro {bp(regression.total.holdout_rmse)}</small></div></div><p className="method-inline">{regression.adjustment_convention} {regression.points.length} intervalos alinhados com as mesmas variáveis.</p></div>}
      {impactError && <p className="equity-note">Estudo de documentos: {impactError}</p>}
      {impact && <div className="local-impact"><div className="panel-header"><div><span className="section-kicker">DOCUMENTOS DA COMPANHIA</span><h3>Movimento após fatos relevantes</h3><p>Referência estimada com até 60 sessões anteriores a cada documento.</p></div><span className="panel-tag">CVM · MODELO PRÉ-EVENTO</span></div><div className="local-impact-grid"><div className="local-impact-list">{impact.events.map((item) => <button type="button" key={item.filing_id} className={activeImpact?.filing_id === item.filing_id ? "selected" : ""} onClick={() => setSelectedImpact(item.filing_id)}><span>{dateLabel(item.published_at)}</span><strong>{item.title.replace("Fato Relevante: ", "")}</strong><small>{item.windows["3"]?.available ? "JANELA DISPONÍVEL" : "SEM AMOSTRA SUFICIENTE"}</small></button>)}</div><div className="local-impact-detail">{activeImpact ? <><a href={activeImpact.source_url} target="_blank" rel="noreferrer">ABRIR NA CVM ↗</a><h4>{activeImpact.title.replace("Fato Relevante: ", "")}</h4><p>Documento em {dateLabel(activeImpact.published_at)} · primeiro pregão analisado: {activeImpact.effective_session ? dateLabel(activeImpact.effective_session) : "indisponível"} · {activeImpact.train_count} sessões no ajuste prévio.</p><div className="horizon-switch" role="group" aria-label="Janela do fato relevante">{([1, 3, 5] as const).map((value) => <button type="button" key={value} className={impactHorizon === value ? "selected" : ""} aria-pressed={impactHorizon === value} onClick={() => setImpactHorizon(value)}>{value} {value === 1 ? "pregão" : "pregões"}</button>)}</div>{window?.available ? <div className="impact-grid"><div className="metric"><span>AÇÃO OBSERVADA</span><strong>{signed(window.observed_return)}</strong><small>retorno total</small></div><div className="metric"><span>MODELO ANTERIOR</span><strong>{signed(window.benchmark_return)}</strong><small>fatores de mercado</small></div><div className="metric"><span>DIFERENÇA</span><strong>{signed(window.abnormal_return)}</strong><small>observado menos esperado</small></div></div> : <div className="empty">Evidência indisponível: {window?.reason ?? activeImpact.reason ?? "sem observações"}.</div>}<div className="cohort-note"><strong>{cohort?.sample_count ?? 0} eventos comparáveis</strong><p>Média da diferença: {signed(cohort?.mean_abnormal_return ?? null)}. Intervalo de 95%: {cohort?.confidence_interval ? `${signed(cohort.confidence_interval[0])} a ${signed(cohort.confidence_interval[1])}` : "indisponível"}.</p></div></> : <div className="empty">Nenhum fato relevante neste recorte.</div>}</div></div><p className="method-inline">{impact.method_note}</p></div>}
    </>}
  </section>;
}
