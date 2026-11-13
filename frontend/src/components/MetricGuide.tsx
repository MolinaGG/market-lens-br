import type { EventWindow, Events, FilingImpact, RegressionFit } from "../types";

type GuideItem = { label: string; text: string };

const percent = (value: number) => `${(value * 100).toFixed(2)}%`;
const points = (value: number) => `${value >= 0 ? "+" : ""}${(value * 100).toFixed(2)} p.p.`;
const basis = (value: number) => `${(value * 10_000).toFixed(2)} bp`;

function Guide({ title, items }: { title: string; items: GuideItem[] }) {
  return <aside className="reading-guide" aria-label={title}>
    <div className="reading-guide-title"><span>COMO INTERPRETAR</span><h3>{title}</h3></div>
    <div className="reading-guide-grid">{items.map((item) => <div key={item.label}><strong>{item.label}</strong><p>{item.text}</p></div>)}</div>
  </aside>;
}

export function SummaryGuide({ aligned, payments, holdout, events }: { aligned: number; payments: number; holdout: number; events: number }) {
  return <Guide title="O tamanho da evidência" items={[
    { label: "Observações alinhadas", text: `${aligned} intervalos de retorno têm cotações e todos os fatores escolhidos nas mesmas datas. Mais intervalos ampliam a amostra, sem eliminar vieses.` },
    { label: "Cupons registrados", text: `${payments} pagamentos por unidade entram no retorno total bruto quando caem entre duas cotações. O preço isolado não os inclui.` },
    { label: "Teste fora da amostra", text: `${holdout} intervalos finais ficam fora do ajuste e servem para medir erro. São dados históricos posteriores ao treino, não uma previsão ao vivo.` },
    { label: "Eventos comparáveis", text: `${events} comunicados têm janela completa de três pregões sem sobreposição na média. Esse número pode ser menor que o total de comunicados.` },
    { label: "Índice base 100", text: "No gráfico, 110 significa retorno acumulado de 10% desde o início da amostra alinhada. A distância entre as linhas mostra o efeito acumulado dos cupons nessa convenção." },
  ]} />;
}

export function RegressionGuide({ fit, modeLabel, factorName }: { fit: RegressionFit; modeLabel: string; factorName: (id: string) => string }) {
  const factors = Object.entries(fit.coefficients).filter(([id]) => id !== "intercept");
  return <Guide title={`A regressão ${modeLabel.toLowerCase()}`} items={[
    { label: "R² no treino", text: `${percent(fit.r_squared)} da variação dos retornos no período de ajuste é descrita por esta combinação linear de fatores. R² maior no treino não garante menor erro depois.` },
    { label: "Erro no teste (RMSE)", text: `${basis(fit.holdout_rmse)} é a escala do erro nos ${fit.holdout_count} intervalos reservados. Menor é melhor na mesma amostra; 100 bp equivalem a 1 ponto percentual de retorno.` },
    { label: "Erro no treino", text: `${basis(fit.train_rmse)} resume a distância típica entre retorno observado e ajustado nos ${fit.train_count} intervalos usados para estimar os coeficientes. Compare-o ao erro no teste para avaliar a estabilidade.` },
    { label: "Coeficientes", text: `${factors.map(([id, beta]) => `${factorName(id)}: ${points(beta * 0.01)} no retorno para uma alta de ${id === "BCB:SGS:11" ? "0,01 p.p. na taxa diária" : "1% no fator"}`).join("; ")}. São associações com os outros fatores mantidos constantes.` },
    { label: "Intercepto", text: `${points(fit.coefficients.intercept ?? 0)} é o retorno diário estimado quando as mudanças de todos os fatores são zero; não representa um rendimento garantido.` },
    { label: "Intervalo de 95%", text: "Mostra valores compatíveis com cada coeficiente sob as hipóteses da OLS. Se atravessa zero, o sinal não está bem determinado neste ajuste. Não é uma faixa para o próximo retorno." },
  ]} />;
}

export function EventGuide({ window, cohort, horizon }: { window: EventWindow | undefined; cohort: Events["cohort"][string] | undefined; horizon: number }) {
  if (!window?.available) return <Guide title="A janela do comunicado" items={[{ label: "Sem medida", text: "Faltam sessões comparáveis antes ou depois do comunicado. A ausência de resultado não significa retorno igual a zero." }]} />;
  return <Guide title="O movimento após o comunicado" items={[
    { label: "Retorno observado", text: `${percent(window.observed_return!)} é o retorno bruto acumulado do título nos ${horizon} pregões após o comunicado.` },
    { label: "Referência e diferença", text: `A referência teve ${percent(window.benchmark_return!)}. A diferença de ${points(window.abnormal_return!)} mede quanto o título ficou acima ou abaixo dela nessa janela; não isola a causa.` },
    { label: "Média e intervalo", text: `${cohort?.sample_count ?? 0} eventos sem janelas sobrepostas entram na média; ${cohort?.excluded_overlap ?? 0} janelas sobrepostas ficam de fora. O intervalo de 95%, quando existe, descreve a incerteza dessa média sob hipóteses estatísticas; não prevê o próximo evento.` },
  ]} />;
}

export function SecurityImpactGuide({ ticker, filing, window, cohort, horizon, mode }: { ticker: string; filing: FilingImpact; window: EventWindow | undefined; cohort: Events["cohort"][string] | undefined; horizon: number; mode: "price" | "total" }) {
  if (!window?.available) return <Guide title={`Leitura de ${ticker} após a divulgação`} items={[{ label: "Sem medida", text: filing.status === "cancelled" ? "Documento cancelado: o histórico é preservado, mas não gera estudo de retorno." : "Faltam sessões suficientes antes ou depois da divulgação para este papel e janela." }]} />;
  const cashDifference = filing.windows[String(horizon)]?.observed_return != null && filing.price_windows[String(horizon)]?.observed_return != null
    ? filing.windows[String(horizon)].observed_return! - filing.price_windows[String(horizon)].observed_return!
    : null;
  return <Guide title={`Leitura de ${ticker} após a divulgação`} items={[
    { label: "O papel negociado", text: `${ticker} teve ${percent(window.observed_return!)} de retorno ${mode === "price" ? "de preço, com desdobramentos neutralizados" : "total bruto, incluindo dividendos e JCP"} nos ${horizon} pregões posteriores.` },
    { label: "Referência anterior", text: `O modelo ajustado com ${filing.train_count} sessões anteriores esperaria ${percent(window.benchmark_return!)} com os fatores realizados nessa janela. É um referencial ex post, não uma previsão negociável.` },
    { label: "Diferença observada", text: `${points(window.abnormal_return!)} é retorno observado menos referência. Um valor positivo indica desempenho acima do modelo. Isso não prova que a divulgação causou o movimento.` },
    { label: "Papel dos proventos", text: cashDifference == null ? "A comparação requer as duas janelas completas." : `${points(cashDifference)} é a diferença entre retornos observados com e sem proventos nesta janela. ${cohort?.sample_count ?? 0} divulgações comparáveis entram na média exibida.` },
    { label: "Média de divulgações", text: `A média reúne ${cohort?.sample_count ?? 0} janelas completas sem sobreposição; ${cohort?.excluded_overlap ?? 0} janelas sobrepostas foram excluídas. O intervalo de 95% expressa a incerteza da média sob hipóteses estatísticas, não prevê outra divulgação.` },
  ]} />;
}
