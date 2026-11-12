import { useEffect, useState } from "react";

type Health = {
  status: string;
  horizon_pregoes: number;
  ativos: string[];
  integracoes: { apify: boolean; groq: boolean };
};

export function App() {
  const [health, setHealth] = useState<Health | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/health")
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json() as Promise<Health>;
      })
      .then(setHealth)
      .catch((e: Error) => setErro(e.message));
  }, []);

  return (
    <main style={{ fontFamily: "system-ui, sans-serif", padding: "2rem", maxWidth: 960 }}>
      <h1>market-lens-br</h1>
      <p>
        Entenda notícias e investigue seus possíveis efeitos nos próximos pregões.
        Projeções são estimativas com incerteza, não recomendação de investimento.
      </p>

      <h2>Status do serviço</h2>
      {erro && <p>Backend indisponível: {erro}</p>}
      {!erro && !health && <p>Carregando…</p>}
      {health && (
        <ul>
          <li>Situação: {health.status}</li>
          <li>Horizonte: {health.horizon_pregoes} pregões</li>
          <li>Apify: {health.integracoes.apify ? "configurado" : "não configurado"}</li>
          <li>Groq: {health.integracoes.groq ? "configurado" : "não configurado"}</li>
        </ul>
      )}

      <h2>Ativos do escopo inicial</h2>
      <ul>
        {(health?.ativos ?? []).map((a) => (
          <li key={a}>{a}</li>
        ))}
      </ul>

      <p><em>Dashboard de notícias e projeções: em construção.</em></p>
    </main>
  );
}
