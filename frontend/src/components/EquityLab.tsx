import { useEffect, useState } from "react";
import { api } from "../api";
import type { LocalNewsImpact, Regression, Series } from "../types";
import { RegressionGuide, SecurityImpactGuide } from "./MetricGuide";
import { ReturnChart } from "./ReturnChart";

const pct = (value: number) => `${(value * 100).toFixed(2)}%`;
const bp = (value: number) => `${(value * 10_000).toFixed(2)} bp`;
const signed = (value: number | null | undefined) => value == null ? "—" : `${value > 0 ? "+" : ""}${pct(value)}`;
const signedPp = (value: number | null | undefined) => value == null ? "—" : `${value > 0 ? "+" : ""}${(value * 100).toFixed(2)} p.p.`;
const dateLabel = (value: string) => new Date(`${value.slice(0, 10)}T12:00:00`).toLocaleDateString("pt-BR", { day: "2-digit", month: "short", year: "numeric" });
const factorName = (id: string) => id.endsWith(":1") ? "USD/BRL" : id.endsWith(":11") ? "Selic" : id === "EIA:BRENT" ? "Brent" : id;
const reasonLabel: Record<string, string> = {
  filing_cancelled: "o documento foi cancelado",
  insufficient_pre_event_model: "faltam pregões anteriores para ajustar o modelo",
  insufficient_pre_event: "faltam pregões anteriores comparáveis",
  rank_deficient_factors: "as variáveis escolhidas não permitem estimar este modelo",
  insufficient_post_event: "faltam pregões posteriores nesta janela",
  no_post_event_session: "ainda não há pregão após a divulgação",
};

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

  useEffect(() => {
    api.localStatus().then((value) => setEnabled(value.enabled)).catch(() => setEnabled(false)).finally(() => setChecking(false));
  }, []);

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
    } finally {
      setBusy(false);
    }
  }

  const activeImpact = impact?.events.find((item) => item.filing_id === selectedImpact) ?? impact?.events[0];
  const window = mode === "price" ? activeImpact?.price_windows[String(impactHorizon)] : activeImpact?.windows[String(impactHorizon)];
  const cohort = mode === "price" ? impact?.price_cohort[String(impactHorizon)] : impact?.cohort[String(impactHorizon)];

  return <section id="acoes" className="panel equity-panel">
    <div className="panel-header">
      <div><span className="section-kicker">06 / AÇÕES & PROVENTOS</span><h2>Repita o estudo com uma ação.</h2><p>Preços e eventos importados pelo pesquisador ficam somente no banco local.</p></div>
      <span className="panel-tag">PESQUISA LOCAL</span>
    </div>
    {checking ? <p className="equity-note">Verificando a pesquisa local…</p> : !enabled ? <div className="equity-disabled">
      <strong>Disponível na execução local do projeto.</strong>
      <p>A demonstração pública não recebe arquivos de preços de ações. Ao executar o projeto no seu computador, ative a importação local e use seus próprios CSVs.</p>
      <a href="https://github.com/MolinaGG/market-lens-br#executar-localmente" target="_blank" rel="noreferrer">Ver instruções no projeto ↗</a>
    </div> : <>
      <div className="equity-import">
        <label><span>1 · PREÇOS DIÁRIOS</span><input type="file" accept=".csv,text/csv" onChange={(event) => setPricesFile(event.target.files?.[0] ?? null)} /><small>Colunas: ticker, date, close</small></label>
        <label><span>2 · DESDOBRAMENTOS E PROVENTOS</span><input type="file" accept=".csv,text/csv" onChange={(event) => setActionsFile(event.target.files?.[0] ?? null)} /><small>ticker, ex_date, kind, amount, split_factor</small></label>
        <button type="button" disabled={busy || !pricesFile || !actionsFile} onClick={importFiles}>{busy ? "Analisando…" : "Importar e comparar →"}</button>
      </div>
      <p className="equity-note">Datas em AAAA-MM-DD; <code>kind</code> aceita dividend, jcp e split. Valor é por ação na data ex. O servidor público bloqueia esta operação.</p>
      {error && <div className="equity-error" role="alert">{error}</div>}
      {series && <p className="equity-note">{ticker}: {series.observations.length} preços e {series.cash_flows.length} proventos validados.</p>}
      {series && regression && <div className="equity-result">
        <div className="equity-result-head">
          <strong>{ticker} · comparação de retornos</strong>
          <div className="mode-switch" role="group" aria-label="Modo de retorno da ação e dos eventos">
            <button type="button" className={mode === "price" ? "selected" : ""} aria-pressed={mode === "price"} onClick={() => setMode("price")}>Só preço</button>
            <button type="button" className={mode === "total" ? "selected" : ""} aria-pressed={mode === "total"} onClick={() => setMode("total")}>Com proventos</button>
          </div>
        </div>
        <ReturnChart points={regression.points} couponDates={series.cash_flows.map((flow) => flow.date)} mode={mode} cashLabel="proventos" />
        <p className="method-inline">Base 100 no primeiro preço: 110 representa ganho acumulado de 10%. O botão também muda a leitura das divulgações abaixo.</p>
        <div className="equity-comparison">
          <div><span>SEM PROVENTOS</span><strong>R² {pct(regression.price.r_squared)}</strong><small>Erro no teste {bp(regression.price.holdout_rmse)}</small></div>
          <div><span>COM PROVENTOS</span><strong>R² {pct(regression.total.r_squared)}</strong><small>Erro no teste {bp(regression.total.holdout_rmse)}</small></div>
        </div>
        <p className="method-inline">{regression.adjustment_convention} {regression.points.length} intervalos alinhados com as mesmas variáveis.</p>
        <RegressionGuide fit={regression[mode]} modeLabel={mode === "price" ? "sem proventos" : "com proventos"} factorName={factorName} />
      </div>}
      {impactError && <p className="equity-note">Estudo de documentos: {impactError}</p>}
      {impact && <div className="local-impact">
        <div className="panel-header">
          <div><span className="section-kicker">DOCUMENTOS DA COMPANHIA</span><h3>O que aconteceu com {ticker} após cada divulgação?</h3><p>Fatos relevantes e comunicados ao mercado da CVM. Referência estimada com até 60 pregões anteriores.</p></div>
          <span className="panel-tag">CVM · MODELO PRÉ-EVENTO</span>
        </div>
        <div className="local-impact-grid">
          <div className="local-impact-list">
            {impact.events.map((item) => {
              const selectedWindow = mode === "price" ? item.price_windows[String(impactHorizon)] : item.windows[String(impactHorizon)];
              return <button type="button" key={item.filing_id} className={activeImpact?.filing_id === item.filing_id ? "selected" : ""} onClick={() => setSelectedImpact(item.filing_id)}>
                <span>{dateLabel(item.published_at)} · {item.category}</span>
                <strong>{item.title.replace(/^(Fato Relevante|Comunicado ao Mercado): /, "")}</strong>
                <small>{item.status === "cancelled" ? "CANCELADO" : selectedWindow?.available ? "JANELA DISPONÍVEL" : "SEM MEDIDA NESTA JANELA"}</small>
              </button>;
            })}
          </div>
          <div className="local-impact-detail">
            {activeImpact ? <>
              <a href={activeImpact.source_url} target="_blank" rel="noreferrer">ABRIR NA CVM ↗</a>
              <h4>{activeImpact.title.replace(/^(Fato Relevante|Comunicado ao Mercado): /, "")}</h4>
              <p>{activeImpact.category} em {dateLabel(activeImpact.published_at)} · primeiro pregão analisado: {activeImpact.effective_session ? dateLabel(activeImpact.effective_session) : "indisponível"} · {activeImpact.train_count} pregões no ajuste anterior.</p>
              <div className="horizon-switch" role="group" aria-label="Janela após divulgação">
                {([1, 3, 5] as const).map((value) => <button type="button" key={value} className={impactHorizon === value ? "selected" : ""} aria-pressed={impactHorizon === value} onClick={() => setImpactHorizon(value)}>{value} {value === 1 ? "pregão" : "pregões"}</button>)}
              </div>
              {window?.available ? <div className="impact-grid">
                <div className="metric"><span>{ticker} · OBSERVADO</span><strong>{signed(window.observed_return)}</strong><small>{mode === "price" ? "retorno de preço" : "retorno com proventos"}</small></div>
                <div className="metric"><span>MODELO ANTERIOR</span><strong>{signed(window.benchmark_return)}</strong><small>fatores realizados</small></div>
                <div className="metric"><span>DIFERENÇA</span><strong>{signedPp(window.abnormal_return)}</strong><small>observado menos esperado</small></div>
              </div> : <div className="empty">Medida indisponível: {reasonLabel[window?.reason ?? activeImpact.reason ?? ""] ?? "sem observações comparáveis"}.</div>}
              <div className="cohort-note"><strong>{cohort?.sample_count ?? 0} divulgações comparáveis · {mode === "price" ? "só preço" : "com proventos"}</strong>
                <p>Média da diferença: {signedPp(cohort?.mean_abnormal_return)}. Intervalo de 95%: {cohort?.confidence_interval ? `${signedPp(cohort.confidence_interval[0])} a ${signedPp(cohort.confidence_interval[1])}` : "indisponível"}.</p>
              </div>
              <SecurityImpactGuide ticker={ticker} filing={activeImpact} window={window} cohort={cohort} horizon={impactHorizon} mode={mode} />
            </> : <div className="empty">Nenhuma divulgação CVM neste recorte.</div>}
          </div>
        </div>
        <p className="method-inline">{impact.method_note} Notícias jornalísticas aparecem como contexto na seção anterior; sua detecção não é usada como data de evento.</p>
      </div>}
    </>}
  </section>;
}
