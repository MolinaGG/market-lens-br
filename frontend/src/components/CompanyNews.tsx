import { useEffect, useState } from "react";
import { api } from "../api";
import type { CompanyNews as CompanyNewsData } from "../types";

const companies = [
  ["PETR4", "Petrobras"], ["VALE3", "Vale"], ["ITUB4", "Itaú"],
  ["BBDC4", "Bradesco"], ["WEGE3", "WEG"], ["ABEV3", "Ambev"],
];
const dateLabel = (value: string) => new Date(`${value.slice(0, 10)}T12:00:00`).toLocaleDateString("pt-BR", { day: "2-digit", month: "short", year: "numeric" });

export function CompanyNews() {
  const [ticker, setTicker] = useState("BBDC4");
  const [data, setData] = useState<CompanyNewsData | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    api.companyNews(ticker, controller.signal).then((value) => {
      setData(value);
      setSelected(value.filings[0]?.filing_id ?? null);
      setLoading(false);
    }).catch((reason: Error) => {
      if (reason.name !== "AbortError") { setError(reason.message); setLoading(false); }
    });
    return () => controller.abort();
  }, [ticker]);

  const filing = data?.filings.find((item) => item.filing_id === selected) ?? data?.filings[0];
  return <section id="companhias" className="panel company-panel"><div className="panel-header"><div><span className="section-kicker">05 / DOCUMENTOS & COBERTURA</span><h2>O que a companhia divulgou?</h2><p>Fatos relevantes e comunicados da CVM, com contexto de notícias detectadas pelo GDELT.</p></div><span className="panel-tag">CVM · GDELT</span></div>
    <div className="company-tabs" role="group" aria-label="Companhia">{companies.map(([code, name]) => <button type="button" key={code} className={ticker === code ? "selected" : ""} aria-pressed={ticker === code} onClick={() => setTicker(code)}><strong>{code}</strong><small>{name}</small></button>)}</div>
    {loading && <p className="equity-note" role="status">Carregando documentos da companhia…</p>}
    {error && <div className="equity-error" role="alert">{error}</div>}
    {data && !error && <><div className="company-grid"><div className="company-filings"><div className="company-subhead">PUBLICAÇÕES CVM <span>{data.filings.length} MAIS RECENTES</span></div><div className="company-scroll">{data.filings.map((item) => <button type="button" key={item.filing_id} className={filing?.filing_id === item.filing_id ? "selected" : ""} onClick={() => setSelected(item.filing_id)}><span>{dateLabel(item.published_at)} · {item.category}</span><strong>{item.title.replace(`${item.category}: `, "")}</strong><small>{item.status === "refiled" ? "REAPRESENTADO" : item.status === "cancelled" ? "CANCELAMENTO" : "DOCUMENTO ORIGINAL"}</small></button>)}</div></div><div className="company-detail">{filing ? <><span className="company-detail-label">{filing.category.toUpperCase()} · CVM {filing.company_code}</span><h3>{filing.title.replace(`${filing.category}: `, "")}</h3><p>Entrega em {dateLabel(filing.published_at)} · versão {filing.version} · {filing.status === "refiled" ? "reapresentado" : filing.status === "cancelled" ? "cancelamento" : "apresentação original"}.</p><a href={filing.source_url} target="_blank" rel="noreferrer">ABRIR DOCUMENTO NA CVM ↗</a><div className="company-method">O arquivo informa o dia da entrega, sem horário. Qualquer estudo de preços começa no pregão seguinte. Documentos cancelados ficam fora da amostra de impacto.</div></> : <div className="empty">Sem documentos recentes para esta companhia.</div>}</div></div><div className="coverage-section"><div className="company-subhead">MENÇÕES EM NOTÍCIAS <span>METADADOS GDELT · {data.articles.length} LINKS</span></div><div className="coverage-grid">{data.articles.slice(0, 3).map((item) => <a key={item.source_url} href={item.source_url} target="_blank" rel="noreferrer"><span>{item.domain} · detectado em {dateLabel(item.seen_at)}</span><strong>{item.title}</strong><small>LER NA FONTE ↗ · IMPACTO NÃO MENSURADO: PUBLICAÇÃO NÃO VERIFICADA</small></a>)}{data.articles.length === 0 && <p className="empty">Sem referências disponíveis para esta companhia no retrato de cobertura recente.</p>}</div><p className="coverage-note">Retrato {data.version} · coletado em {dateLabel(data.fetched_at)}. O horário GDELT registra detecção, não publicação confirmada. Os títulos passam por filtro do nome da companhia, mas podem tratar de outros assuntos. Os links servem de contexto e não entram no cálculo de impacto. Fonte dos metadados: <a href="https://gdeltproject.org/about.html" target="_blank" rel="noreferrer">GDELT Project ↗</a></p></div><div className="company-action-note">Na <a href="#acoes">pesquisa local abaixo</a>, importe preços e proventos para medir o movimento após divulgações da CVM. Um terceiro CSV opcional permite estudar notícias com data e fonte verificadas. Compare os dois modos de retorno diante de modelos ajustados apenas com sessões anteriores.</div></>}
  </section>;
}
