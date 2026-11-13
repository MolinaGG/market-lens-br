import { useEffect, useMemo, useState } from "react";
import { api } from "./api";
import { ReturnChart } from "./components/ReturnChart";
import { EquityLab } from "./components/EquityLab";
import type { Catalog, Events, Regression, Series } from "./types";
import "./styles.css";

const dateLabel = (value: string) => new Date(`${value.slice(0, 10)}T12:00:00`).toLocaleDateString("pt-BR", { day: "2-digit", month: "short", year: "numeric" });
const pct = (value: number | null | undefined) => value == null ? "—" : `${(value * 100).toFixed(2)}%`;
const signed = (value: number | null | undefined) => value == null ? "—" : `${value > 0 ? "+" : ""}${pct(value)}`;
const num = (value: number, digits = 2) => new Intl.NumberFormat("pt-BR", { minimumFractionDigits: digits, maximumFractionDigits: digits }).format(value);
const factorName = (id: string) => id.endsWith(":1") ? "USD/BRL" : id.endsWith(":11") ? "Selic" : id;

function Metric({ label, value, note }: { label: string; value: string; note: string }) {
  return <div className="metric"><span>{label}</span><strong>{value}</strong><small>{note}</small></div>;
}

export function App() {
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [instrumentId, setInstrumentId] = useState("");
  const [factorIds, setFactorIds] = useState<string[]>(["BCB:SGS:1", "BCB:SGS:11"]);
  const [series, setSeries] = useState<Series | null>(null);
  const [regression, setRegression] = useState<Regression | null>(null);
  const [events, setEvents] = useState<Events | null>(null);
  const [mode, setMode] = useState<"price" | "total">("total");
  const [horizon, setHorizon] = useState<1 | 3 | 5>(3);
  const [selectedEvent, setSelectedEvent] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    api.catalog(controller.signal).then((value) => {
      setCatalog(value);
      setInstrumentId(value.default_instrument_id);
      setLoading(false);
    }).catch((reason: Error) => {
      if (reason.name !== "AbortError") { setError(reason.message); setLoading(false); }
    });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (!catalog || !instrumentId) return;
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    Promise.all([
      api.series(instrumentId, controller.signal),
      api.regression(instrumentId, factorIds, controller.signal),
      api.events(instrumentId, catalog.benchmark_id, controller.signal),
    ]).then(([nextSeries, nextRegression, nextEvents]) => {
      setSeries(nextSeries);
      setRegression(nextRegression);
      setEvents(nextEvents);
      setSelectedEvent(nextEvents.events[0]?.event_id ?? null);
      setLoading(false);
    }).catch((reason: Error) => {
      if (reason.name !== "AbortError") { setError(reason.message); setLoading(false); }
    });
    return () => controller.abort();
  }, [catalog, instrumentId, factorIds]);

  const instruments = useMemo(() => catalog?.instruments.filter((item) => item.cash_flow_count > 0 && item.observation_count >= 200) ?? [], [catalog]);
  const selectedSeries = catalog?.instruments.find((item) => item.series_id === instrumentId);
  const activeFit = regression?.[mode];
  const activeEvent = events?.events.find((item) => item.event_id === selectedEvent) ?? events?.events[0];
  const activeWindow = activeEvent?.windows[String(horizon)];
  const cohort = events?.cohort[String(horizon)];

  function toggleFactor(id: string) {
    setFactorIds((current) => current.includes(id) ? current.length > 1 ? current.filter((item) => item !== id) : current : [...current, id]);
  }

  return <div className="app-shell">
    <aside className="sidebar">
      <a className="brand" href="#inicio" aria-label="Market Lens, início"><span className="brand-mark"><i /></span><span>market<b>lens</b><small>BR / QUANT RESEARCH</small></span></a>
      <div className="sidebar-label">EXPLORAR</div>
      <nav aria-label="Navegação principal"><a className="active" href="#inicio">◫ <span>Visão geral</span></a><a href="#retornos">⌁ <span>Retornos</span></a><a href="#regressao">▥ <span>Regressão</span></a><a href="#eventos">◉ <span>Eventos & notícias</span></a><a href="#acoes">◇ <span>Ações locais</span></a><a href="#metodo">▤ <span>Metodologia</span></a></nav>
      <div className="sidebar-bottom"><span className="status-dot" /> DADOS ABERTOS · REPRODUZÍVEIS <p>Tesouro Transparente + Banco Central</p></div>
    </aside>
    <main id="inicio" className="main-content">
      <header className="topbar"><span>PESQUISA <i>/</i> MERCADO BRASILEIRO <i>/</i> TÍTULOS PÚBLICOS</span><span><span className="status-dot" /> RETRATO HISTÓRICO <i>/</i> VERSÃO {catalog?.version.slice(0, 8) ?? "—"}</span></header>
      <div className="content">
        <section className="hero"><div className="eyebrow"><i /> LABORATÓRIO QUANTITATIVO <span>01 / 04</span></div><h1>O que o preço<br /><em>sozinho</em> não conta.</h1><p>Investigue retornos, cupons e comunicados do Copom com dados oficiais. Compare a mesma regressão antes e depois do ajuste por pagamentos.</p><div className="hero-meta">FONTE: TESOURO + BCB <span>·</span> ATUALIZADO EM {catalog ? dateLabel(catalog.fetched_at) : "—"}</div></section>
        {loading && !catalog && <div className="state-panel" role="status">Carregando o retrato de pesquisa…</div>}
        {error && <div className="state-panel error" role="alert"><strong>Não foi possível carregar a pesquisa.</strong><p>{error}</p><small>Verifique se a API está ativa e se o retrato de dados foi criado.</small></div>}
        {catalog && <>
          <section className="control-panel" aria-label="Configuração da pesquisa"><div className="panel-header"><div><span className="section-kicker">01 / DEFINIR PESQUISA</span><h2>Selecione o título e as variáveis</h2></div><span className="panel-tag">MESMA AMOSTRA · DOIS RETORNOS</span></div><div className="control-grid"><label className="field"><span>TÍTULO COM CUPOM</span><select value={instrumentId} onChange={(event) => setInstrumentId(event.target.value)}>{instruments.map((item) => <option key={item.series_id} value={item.series_id}>{item.name}</option>)}</select></label><div className="field"><span>VARIÁVEIS EXPLICATIVAS</span><div className="factor-options">{catalog.factors.filter((item) => ["BCB:SGS:1", "BCB:SGS:11"].includes(item.series_id)).map((item) => <label className="factor-chip" key={item.series_id}><input type="checkbox" checked={factorIds.includes(item.series_id)} onChange={() => toggleFactor(item.series_id)} />{factorName(item.series_id)}</label>)}</div></div></div><div className="control-foot"><span>IPCA mensal aguarda regra de divulgação e licença verificadas para entrar na demonstração.</span><span>{selectedSeries ? `${dateLabel(selectedSeries.start_date)} — ${dateLabel(selectedSeries.end_date)}` : ""}</span></div></section>
          {loading && <div className="inline-loading" role="status">Atualizando resultados para a seleção…</div>}
          {series && regression && events && !error && <>
            <section className="metrics-row" aria-label="Resumo"><Metric label="OBSERVAÇÕES ALINHADAS" value={num(regression.points.length, 0)} note="mesmas datas nos dois modelos" /><Metric label="CUPONS REGISTRADOS" value={num(series.cash_flows.length, 0)} note="pagamentos por unidade" /><Metric label="VALIDAÇÃO FUTURA" value={num(regression.total.holdout_count, 0)} note="pontos fora da amostra" /><Metric label="EVENTOS COM EVIDÊNCIA" value={num(events.cohort["3"]?.sample_count ?? 0, 0)} note="janelas de 3 pregões" /></section>
            <section id="retornos" className="panel returns-panel"><div className="panel-header"><div><span className="section-kicker">02 / RETORNO HISTÓRICO</span><h2>O efeito dos cupons no retorno</h2><p>Índice acumulado · base 100 no início da série alinhada</p></div><div className="mode-switch" role="group" aria-label="Retorno destacado"><button type="button" className={mode === "price" ? "selected" : ""} aria-pressed={mode === "price"} onClick={() => setMode("price")}>Só preço</button><button type="button" className={mode === "total" ? "selected" : ""} aria-pressed={mode === "total"} onClick={() => setMode("total")}>Com cupons</button></div></div><ReturnChart points={regression.points} couponDates={series.cash_flows.map((flow) => flow.date)} mode={mode} /><div className="chart-footer"><span>LINHAS: PREÇO E RETORNO TOTAL BRUTO</span><span>{regression.points.length} INTERVALOS · ATÉ {dateLabel(regression.points[regression.points.length - 1].date)}</span></div></section>
            <section id="regressao" className="panel regression-panel"><div className="panel-header"><div><span className="section-kicker">03 / RELAÇÃO COM O MERCADO</span><h2>A mesma regressão, dois resultados.</h2><p>{factorIds.map(factorName).join(" + ")} · treino até {dateLabel(regression.train_end)}</p></div><span className="panel-tag">OLS · IC DE 95%</span></div><div className="comparison">{(["price", "total"] as const).map((key) => { const fit = regression[key]; return <div key={key} className={`fit-card ${key === "total" ? "adjusted-card" : ""} ${mode === key ? "fit-active" : ""}`}><span className="fit-overline">{key === "price" ? "RETORNO DE PREÇO" : "RETORNO TOTAL BRUTO"}</span><h3>{key === "price" ? "Sem cupons" : "Com cupons"}</h3><strong className="fit-number">{pct(fit.r_squared)}</strong><span className="fit-subtitle">R² no treino</span><div className="fit-divider" /><div className="fit-detail"><span>Erro futuro (RMSE)</span><strong>{num(fit.holdout_rmse * 10000)} bp</strong></div><div className="fit-detail"><span>Treino + teste</span><strong>{fit.train_count} + {fit.holdout_count}</strong></div></div>; })}</div><div className="regression-insight"><span>↗</span><div><strong>Diferença mensurável</strong><p>O R² muda {signed(regression.total.r_squared - regression.price.r_squared)} e o erro futuro muda {num((regression.total.holdout_rmse - regression.price.holdout_rmse) * 10000)} bp após incluir os cupons. A direção pode variar por título e período.</p></div></div><details className="coefficients"><summary>Ver coeficientes e intervalos de 95% do modo selecionado <span>⌄</span></summary><div className="table-scroll"><table><thead><tr><th>Variável</th><th>Coeficiente</th><th>Intervalo de 95%</th></tr></thead><tbody>{Object.entries(activeFit?.coefficients ?? {}).map(([key, value]) => <tr key={key}><td>{key === "intercept" ? "Intercepto" : factorName(key)}</td><td>{num(value, 5)}</td><td>{activeFit?.confidence_intervals[key]?.map((limit) => num(limit, 5)).join(" a ") ?? "—"}</td></tr>)}</tbody></table></div></details><p className="method-inline">{regression.adjustment_convention} As datas e variáveis são idênticas nas duas regressões.</p></section>
            <section id="eventos" className="panel events-panel"><div className="panel-header"><div><span className="section-kicker">04 / NOTÍCIAS & IMPACTO OBSERVADO</span><h2>Depois do comunicado, o que aconteceu?</h2><p>Comunicados oficiais do Copom · referência: Tesouro Prefixado 2029.</p></div><span className="panel-tag">FONTE PRIMÁRIA · BCB</span></div><div className="event-layout"><div className="event-list" role="list" aria-label="Comunicados do Copom">{events.events.map((item) => <button type="button" role="listitem" key={item.event_id} className={`event-item ${activeEvent?.event_id === item.event_id ? "event-selected" : ""}`} onClick={() => setSelectedEvent(item.event_id)}><span className="event-date">{dateLabel(item.published_at)}</span><strong>{item.title}</strong><span className="event-id">COMUNICADO {item.event_id.replace("COPOM:", "#")} ↗</span></button>)}</div><div className="event-detail">{activeEvent ? <><div className="event-detail-top"><span>COMUNICADO DO COPOM</span><a href={activeEvent.source_url} target="_blank" rel="noreferrer">VER ORIGINAL ↗</a></div><h3>{activeEvent.title}</h3><p>Publicado em {dateLabel(activeEvent.published_at)}. Horário não informado; análise a partir do pregão de {activeEvent.effective_session ? dateLabel(activeEvent.effective_session) : "dados disponíveis"}.</p><div className="horizon-switch" role="group" aria-label="Janela do evento">{([1, 3, 5] as const).map((value) => <button type="button" key={value} className={horizon === value ? "selected" : ""} aria-pressed={horizon === value} onClick={() => setHorizon(value)}>{value} {value === 1 ? "pregão" : "pregões"}</button>)}</div>{activeWindow?.available ? <div className="impact-grid"><Metric label="TÍTULO · OBSERVADO" value={signed(activeWindow.observed_return)} note="retorno acumulado" /><Metric label="REFERÊNCIA" value={signed(activeWindow.benchmark_return)} note="Prefixado 2029" /><Metric label="DIFERENÇA" value={signed(activeWindow.abnormal_return)} note="observado menos referência" /></div> : <div className="empty">Dados insuficientes para esta janela ({activeWindow?.reason ?? "sem observações"}).</div>}<div className="cohort-note"><strong>{cohort?.sample_count ?? 0} eventos comparáveis</strong><p>Média da diferença em {horizon} {horizon === 1 ? "pregão" : "pregões"}: {signed(cohort?.mean_abnormal_return)}. Intervalo de 95%: {cohort?.confidence_interval ? `${signed(cohort.confidence_interval[0])} a ${signed(cohort.confidence_interval[1])}` : "indisponível"}.</p></div><p className="event-caveat">Movimento posterior e notícia têm associação temporal. Outros acontecimentos podem explicar o preço.</p></> : <div className="empty">Nenhum comunicado disponível no retrato.</div>}</div></div></section>
            <EquityLab factorIds={factorIds} />
            <section id="metodo" className="method-panel"><div><span className="section-kicker">TRANSPARÊNCIA</span><h2>Dados que você pode conferir.</h2><p>Preços, cupons, câmbio, Selic e comunicados mantêm fonte oficial e data de coleta. O estudo usa um retrato identificado, para que os resultados possam ser reproduzidos.</p></div><div className="source-links"><a href={series.series.source_url} target="_blank" rel="noreferrer">Preços do Tesouro ↗</a>{series.cash_flows[0] && <a href={series.cash_flows[0].source_url} target="_blank" rel="noreferrer">Cupons por unidade ↗</a>}{catalog.factors.filter((item) => factorIds.includes(item.series_id)).map((item) => <a key={item.series_id} href={item.source_url} target="_blank" rel="noreferrer">{factorName(item.series_id)} · BCB ↗</a>)}</div></section>
          </>}
        </>}
        <footer><span>MARKET LENS BR · PESQUISA QUANTITATIVA</span><span>ANÁLISE HISTÓRICA · SEM RECOMENDAÇÃO DE INVESTIMENTO</span></footer>
      </div>
    </main>
  </div>;
}
