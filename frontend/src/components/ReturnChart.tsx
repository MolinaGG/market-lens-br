import type { ReturnPoint } from "../types";

type Props = {
  points: ReturnPoint[];
  couponDates: string[];
  mode: "price" | "total";
};

const W = 900;
const H = 300;
const PAD = { left: 50, right: 16, top: 23, bottom: 35 };

function indexed(points: ReturnPoint[], key: "price_return" | "total_return") {
  let value = 100;
  return points.map((point) => {
    value *= 1 + point[key];
    return value;
  });
}

export function ReturnChart({ points, couponDates, mode }: Props) {
  if (points.length < 2) return <p className="empty">Não há observações suficientes para o gráfico.</p>;
  const raw = indexed(points, "price_return");
  const total = indexed(points, "total_return");
  const min = Math.min(...raw, ...total);
  const max = Math.max(...raw, ...total);
  const range = max - min || 1;
  const x = (index: number) => PAD.left + index / (points.length - 1) * (W - PAD.left - PAD.right);
  const y = (value: number) => PAD.top + (1 - (value - min) / range) * (H - PAD.top - PAD.bottom);
  const path = (values: number[]) => values.map((value, index) => `${index === 0 ? "M" : "L"}${x(index).toFixed(1)},${y(value).toFixed(1)}`).join(" ");
  const ticks = [0, 1, 2, 3, 4];
  const couponIndices = couponDates.map((date) => points.findIndex((point) => point.date >= date)).filter((index) => index >= 0);
  return (
    <div className="chart-wrap">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Índice acumulado do retorno de preço e do retorno com cupons, base 100">
        {ticks.map((tick) => {
          const value = min + range * tick / 4;
          const yy = y(value);
          return <g key={tick}><line x1={PAD.left} x2={W - PAD.right} y1={yy} y2={yy} className="chart-grid" /><text x={PAD.left - 10} y={yy + 4} textAnchor="end" className="chart-axis">{value.toFixed(0)}</text></g>;
        })}
        {couponIndices.map((index) => <line key={index} x1={x(index)} x2={x(index)} y1={PAD.top} y2={H - PAD.bottom} className="chart-coupon" />)}
        <path d={path(raw)} className={`chart-line raw ${mode === "price" ? "active" : ""}`} />
        <path d={path(total)} className={`chart-line adjusted ${mode === "total" ? "active" : ""}`} />
        {[0, Math.floor((points.length - 1) / 2), points.length - 1].map((index) => <text key={index} x={x(index)} y={H - 7} textAnchor={index === 0 ? "start" : index === points.length - 1 ? "end" : "middle"} className="chart-axis">{new Date(`${points[index].date}T12:00:00`).toLocaleDateString("pt-BR", { month: "short", year: "numeric" })}</text>)}
      </svg>
      <div className="chart-legend"><span><i className="line-swatch raw" />Só preço</span><span><i className="line-swatch adjusted" />Preço + cupons</span><span><i className="coupon-swatch" />Pagamento de cupom</span></div>
    </div>
  );
}
