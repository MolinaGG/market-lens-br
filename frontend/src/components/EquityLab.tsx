import { useEffect, useState } from "react";
import { api } from "../api";
import type { Regression, Series } from "../types";
import { ReturnChart } from "./ReturnChart";

const pct = (value: number) => `${(value * 100).toFixed(2)}%`;
const bp = (value: number) => `${(value * 10000).toFixed(2)} bp`;

export function EquityLab({ factorIds }: { factorIds: string[] }) {
  const [enabled, setEnabled] = useState(false);
  const [checking, setChecking] = useState(true);
  const [pricesFile, setPricesFile] = useState<File | null>(null);
  const [actionsFile, setActionsFile] = useState<File | null>(null);
  const [ticker, setTicker] = useState("");
  const [series, setSeries] = useState<Series | null>(null);
  const [regression, setRegression] = useState<Regression | null>(null);
  const [mode, setMode] = useState<"price" | "total">("total");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => { api.localStatus().then((value) => setEnabled(value.enabled)).catch(() => setEnabled(false)).finally(() => setChecking(false)); }, []);

  async function importFiles() {
    if (!pricesFile || !actionsFile) return;
    setBusy(true);
    setError(null);
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
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Não foi possível concluir a importação.");
    } finally { setBusy(false); }
  }

  return <section id="acoes" className="panel equity-panel"><div className="panel-header"><div><span className="section-kicker">05 / AÇÕES & PROVENTOS</span><h2>Repita o estudo com uma ação.</h2><p>Preços e eventos importados pelo pesquisador ficam somente no banco local.</p></div><span className="panel-tag">PESQUISA LOCAL</span></div>
    {checking ? <p className="equity-note">Verificando a pesquisa local…</p> : !enabled ? <div className="equity-disabled"><strong>Disponível na execução local do projeto.</strong><p>A demonstração pública não recebe arquivos de preços de ações. Ao executar o projeto no seu computador, ative a importação local e use seus próprios CSVs.</p><a href="https://github.com/MolinaGG/market-lens-br#executar-localmente" target="_blank" rel="noreferrer">Ver instruções no projeto ↗</a></div> : <>
      <div className="equity-import"><label><span>1 · PREÇOS DIÁRIOS</span><input type="file" accept=".csv,text/csv" onChange={(event) => setPricesFile(event.target.files?.[0] ?? null)} /><small>Colunas: ticker, date, close</small></label><label><span>2 · DESDOBRAMENTOS E PROVENTOS</span><input type="file" accept=".csv,text/csv" onChange={(event) => setActionsFile(event.target.files?.[0] ?? null)} /><small>ticker, ex_date, kind, amount, split_factor</small></label><button type="button" disabled={busy || !pricesFile || !actionsFile} onClick={importFiles}>{busy ? "Analisando…" : "Importar e comparar →"}</button></div>
      <p className="equity-note">Datas em AAAA-MM-DD; `kind` aceita dividend, jcp e split. Valor é por ação na data ex. O servidor público bloqueia esta operação.</p>
      {error && <div className="equity-error" role="alert">{error}</div>}
      {series && <p className="equity-note">{ticker}: {series.observations.length} preços e {series.cash_flows.length} proventos validados.</p>}
      {series && regression && <div className="equity-result"><div className="equity-result-head"><strong>{ticker} · comparação de retornos</strong><div className="mode-switch" role="group" aria-label="Retorno da ação destacado"><button type="button" className={mode === "price" ? "selected" : ""} aria-pressed={mode === "price"} onClick={() => setMode("price")}>Só preço</button><button type="button" className={mode === "total" ? "selected" : ""} aria-pressed={mode === "total"} onClick={() => setMode("total")}>Com proventos</button></div></div><ReturnChart points={regression.points} couponDates={series.cash_flows.map((flow) => flow.date)} mode={mode} cashLabel="proventos" /><div className="equity-comparison"><div><span>SEM PROVENTOS</span><strong>R² {pct(regression.price.r_squared)}</strong><small>Erro futuro {bp(regression.price.holdout_rmse)}</small></div><div><span>COM PROVENTOS</span><strong>R² {pct(regression.total.r_squared)}</strong><small>Erro futuro {bp(regression.total.holdout_rmse)}</small></div></div><p className="method-inline">{regression.adjustment_convention} {regression.points.length} intervalos alinhados com as mesmas variáveis.</p></div>}
    </>}
  </section>;
}
