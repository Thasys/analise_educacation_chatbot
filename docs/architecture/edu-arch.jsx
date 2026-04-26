import { useState } from "react";

const layers = [
  {
    id: "sources",
    label: "CAMADA 0",
    title: "Fontes de Dados",
    color: "#6C9BC7",
    accent: "#4A7FAD",
    description: "Origem dos dados brutos — APIs REST, downloads em lote e repositórios.",
    nodes: [
      { id: "apis", label: "APIs REST", sub: "IBGE SIDRA · IPEADATA · World Bank · UIS · Eurostat · OECD SDMX · CEPALSTAT · UK DfE · NAEP", icon: "⚡" },
      { id: "batch", label: "Downloads em Lote", sub: "INEP ZIP (Censo, SAEB, ENEM, IDEB) · PISA SPSS · TIMSS SPSS · PIRLS · ICCS · TALIS · ERCE CSV", icon: "📦" },
      { id: "repos", label: "Repositórios & SQL", sub: "Base dos Dados (BigQuery) · GitHub llece/erce · dados.gov.br CKAN", icon: "🗄️" },
    ],
  },
  {
    id: "ingestion",
    label: "CAMADA 1",
    title: "Ingestão & Orquestração",
    color: "#E8946A",
    accent: "#C9703E",
    description: "Coleta, agendamento e monitoramento de todos os pipelines de entrada.",
    nodes: [
      { id: "prefect", label: "Prefect 3", sub: "Orquestrador de fluxos · Agendamento · Retry automático · Alertas por e-mail · UI local (port 4200)", icon: "🔄" },
      { id: "collectors", label: "Coletores Python", sub: "requests + httpx para APIs · pandas/pyarrow para SPSS/SAS · sidrapy · ipeadatapy · wbdata · eurostat", icon: "🐍" },
      { id: "edsurvey", label: "EdSurvey / intsvy", sub: "Microdados PISA, TIMSS, PIRLS com plausible values e pesos BRR/Jackknife corretamente aplicados", icon: "📐" },
    ],
  },
  {
    id: "lake",
    label: "CAMADA 2",
    title: "Data Lake (Medallion)",
    color: "#7CB99A",
    accent: "#4E9970",
    description: "Armazenamento hierárquico em três zonas de maturidade dos dados.",
    nodes: [
      { id: "bronze", label: "🥉 Bronze — Raw", sub: "Dados brutos como recebidos · Parquet + JSON · Imutável · Particionado por fonte/ano", icon: "🥉" },
      { id: "silver", label: "🥈 Silver — Cleaned", sub: "Normalizado · Codificações harmonizadas · ISCED padronizado · Joins-chave resolvidos · Schema Delta Lake", icon: "🥈" },
      { id: "gold", label: "🥇 Gold — Analytical", sub: "Datasets analíticos prontos · Indicadores derivados · Séries temporais comparativas BR × Internacional", icon: "🥇" },
    ],
  },
  {
    id: "processing",
    label: "CAMADA 3",
    title: "Processamento & Catálogo",
    color: "#B08FD4",
    accent: "#8B67B8",
    description: "Motor analítico e governança dos metadados dos datasets.",
    nodes: [
      { id: "duckdb", label: "DuckDB", sub: "Motor SQL embarcado · Lê Parquet/Delta diretamente · Até 100 GB em RAM modesta · Zero infra · Python/R nativo", icon: "🦆" },
      { id: "dbt", label: "dbt Core", sub: "Transformações SQL versionadas no Git · Testes de qualidade · Documentação automática · Lineage de dados", icon: "🔧" },
      { id: "catalog", label: "Catálogo (OpenMetadata)", sub: "Descoberta de datasets · Dicionário de variáveis · Linhagem · Propriedade · Busca full-text", icon: "📚" },
    ],
  },
  {
    id: "storage",
    label: "CAMADA 4",
    title: "Armazenamento Estruturado",
    color: "#D4A04A",
    accent: "#B07820",
    description: "Bancos de dados relacionais e metadados operacionais do sistema.",
    nodes: [
      { id: "postgres", label: "PostgreSQL 16", sub: "Metadados · Logs de ingestão · Catálogo relacional · Credenciais · Controle de versão dos schemas", icon: "🐘" },
      { id: "delta", label: "Delta Lake / Parquet", sub: "Formato colunar otimizado · ACID transactions · Time travel · Compactação automática · Lido por DuckDB e Spark", icon: "📂" },
      { id: "mlflow", label: "MLflow (opcional)", sub: "Registro de experimentos ML · Versionamento de modelos preditivos · Reprodutibilidade acadêmica", icon: "🧪" },
    ],
  },
  {
    id: "serving",
    label: "CAMADA 5",
    title: "Análise & Visualização",
    color: "#E87D7D",
    accent: "#C84444",
    description: "Interfaces de consumo para análise exploratória, dashboards e publicação acadêmica.",
    nodes: [
      { id: "superset", label: "Apache Superset", sub: "Dashboards interativos · 50+ tipos de gráfico · SQL Lab · Publicação interna · Conecta direto no DuckDB/Postgres", icon: "📊" },
      { id: "jupyter", label: "JupyterLab + Quarto", sub: "Análise exploratória Python/R · Relatórios reprodutíveis (.qmd) · Exporta PDF/HTML para publicação acadêmica", icon: "📓" },
      { id: "api_out", label: "FastAPI (opcional)", sub: "Endpoint REST para consultas externas · Serve dados para front customizado · Autenticação por token", icon: "🔌" },
    ],
  },
];

const highlights = [
  { label: "Custo de infra adicional", value: "R$ 0", note: "100% open source" },
  { label: "Motor analítico principal", value: "DuckDB", note: "zero config, SQL puro" },
  { label: "Orquestrador", value: "Prefect 3", note: "UI local + retry" },
  { label: "Formato de armazenamento", value: "Delta/Parquet", note: "colunar, comprimido" },
  { label: "Reprodutibilidade", value: "dbt + Git", note: "cada transform versionada" },
  { label: "Padrão do Lake", value: "Medallion", note: "Bronze → Silver → Gold" },
];

const principles = [
  { icon: "🎯", title: "Menos é mais", desc: "DuckDB elimina a necessidade de Spark para escala acadêmica. Suporta dezenas de GBs com SQL puro, sem cluster." },
  { icon: "🔁", title: "Reprodutibilidade total", desc: "dbt versionado no Git garante que cada transformação seja auditável — essencial para publicação acadêmica." },
  { icon: "📐", title: "Plausible Values corretos", desc: "Microdados do PISA/TIMSS/PIRLS exigem EdSurvey ou intsvy — erros metodológicos aqui invalidam qualquer análise." },
  { icon: "🛡️", title: "Imutabilidade na Bronze", desc: "Nunca altere os dados brutos. Toda transformação acontece nas camadas superiores, preservando o dado original." },
  { icon: "📚", title: "Catálogo desde o início", desc: "OpenMetadata evita o caos de variáveis não documentadas — especialmente crítico com 40+ fontes heterogêneas." },
  { icon: "📦", title: "Containerize com Docker", desc: "Prefect + Superset + Postgres + OpenMetadata em docker-compose. Portável entre máquinas e reproduzível." },
];

export default function ArchDiagram() {
  const [active, setActive] = useState(null);
  const [hoveredNode, setHoveredNode] = useState(null);

  const activeLayer = layers.find(l => l.id === active);

  return (
    <div style={{
      fontFamily: "'Georgia', 'Times New Roman', serif",
      background: "#0F1117",
      minHeight: "100vh",
      color: "#E8E4DC",
      padding: "0",
    }}>
      {/* Header */}
      <div style={{
        background: "linear-gradient(135deg, #1A1E2E 0%, #0F1117 100%)",
        borderBottom: "1px solid #2A2E3E",
        padding: "2.5rem 3rem 2rem",
        position: "relative",
        overflow: "hidden",
      }}>
        <div style={{
          position: "absolute", top: 0, right: 0, width: "400px", height: "100%",
          background: "radial-gradient(ellipse at top right, rgba(108,155,199,0.08) 0%, transparent 70%)",
          pointerEvents: "none",
        }} />
        <div style={{ fontSize: "0.7rem", letterSpacing: "0.25em", color: "#6C9BC7", marginBottom: "0.6rem", textTransform: "uppercase" }}>
          Arquitetura de Sistema · Educação Comparada BR × Internacional
        </div>
        <h1 style={{
          fontSize: "clamp(1.6rem, 3vw, 2.4rem)", margin: 0, fontWeight: "400",
          color: "#F0EDE6", letterSpacing: "-0.02em", lineHeight: 1.15,
        }}>
          Data Lakehouse Educacional
        </h1>
        <p style={{ margin: "0.7rem 0 0", color: "#8A8680", fontSize: "0.95rem", maxWidth: "600px", lineHeight: 1.6 }}>
          Arquitetura Medallion · On-premise · Solo/Pequena equipe · 100% Open Source
        </p>
      </div>

      {/* Highlights bar */}
      <div style={{
        background: "#141720",
        borderBottom: "1px solid #1E2230",
        padding: "1rem 3rem",
        display: "flex", gap: "2.5rem", overflowX: "auto",
      }}>
        {highlights.map(h => (
          <div key={h.label} style={{ minWidth: "fit-content" }}>
            <div style={{ fontSize: "0.65rem", color: "#5A5860", textTransform: "uppercase", letterSpacing: "0.1em" }}>{h.label}</div>
            <div style={{ fontSize: "1.05rem", color: "#E8E4DC", fontWeight: "600", marginTop: "0.15rem" }}>{h.value}</div>
            <div style={{ fontSize: "0.7rem", color: "#6C9BC7", marginTop: "0.05rem" }}>{h.note}</div>
          </div>
        ))}
      </div>

      <div style={{ padding: "2rem 3rem", maxWidth: "1200px", margin: "0 auto" }}>

        {/* Architecture Layers */}
        <div style={{ marginBottom: "3rem" }}>
          <div style={{ fontSize: "0.7rem", letterSpacing: "0.2em", color: "#5A5860", textTransform: "uppercase", marginBottom: "1.5rem" }}>
            Clique em uma camada para explorar
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
            {layers.map((layer, li) => (
              <div key={layer.id}>
                {/* Layer header */}
                <div
                  onClick={() => setActive(active === layer.id ? null : layer.id)}
                  style={{
                    display: "flex", alignItems: "center", gap: "1.2rem",
                    padding: "1rem 1.5rem",
                    background: active === layer.id
                      ? `linear-gradient(90deg, ${layer.color}18 0%, ${layer.color}06 100%)`
                      : "#141720",
                    border: `1px solid ${active === layer.id ? layer.color + "60" : "#1E2230"}`,
                    borderRadius: "10px",
                    cursor: "pointer",
                    transition: "all 0.2s",
                  }}
                  onMouseEnter={e => { if (active !== layer.id) e.currentTarget.style.background = "#1A1E2E"; }}
                  onMouseLeave={e => { if (active !== layer.id) e.currentTarget.style.background = "#141720"; }}
                >
                  {/* Connector line on left */}
                  <div style={{
                    width: "3px", height: "36px", borderRadius: "2px",
                    background: `linear-gradient(180deg, ${layer.color} 0%, ${layer.accent} 100%)`,
                    flexShrink: 0,
                  }} />

                  <div style={{ flexShrink: 0 }}>
                    <div style={{ fontSize: "0.6rem", color: layer.color, letterSpacing: "0.2em", textTransform: "uppercase" }}>{layer.label}</div>
                    <div style={{ fontSize: "1.1rem", color: "#F0EDE6", fontWeight: "500", marginTop: "0.1rem" }}>{layer.title}</div>
                  </div>

                  <div style={{ flex: 1, fontSize: "0.82rem", color: "#6A6660", lineHeight: 1.5, paddingLeft: "0.5rem" }}>
                    {layer.description}
                  </div>

                  {/* Node pills preview */}
                  <div style={{ display: "flex", gap: "0.4rem", flexWrap: "wrap", justifyContent: "flex-end", maxWidth: "300px" }}>
                    {layer.nodes.map(n => (
                      <span key={n.id} style={{
                        padding: "0.2rem 0.6rem", borderRadius: "100px",
                        background: layer.color + "20", color: layer.color,
                        fontSize: "0.65rem", fontFamily: "monospace", whiteSpace: "nowrap",
                      }}>{n.label}</span>
                    ))}
                  </div>

                  <div style={{
                    color: layer.color, fontSize: "1rem", flexShrink: 0,
                    transform: active === layer.id ? "rotate(90deg)" : "rotate(0deg)",
                    transition: "transform 0.2s",
                  }}>›</div>
                </div>

                {/* Expanded detail */}
                {active === layer.id && (
                  <div style={{
                    marginTop: "0.5rem",
                    display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
                    gap: "0.75rem",
                    animation: "fadeIn 0.2s ease",
                  }}>
                    {layer.nodes.map(node => (
                      <div
                        key={node.id}
                        onMouseEnter={() => setHoveredNode(node.id)}
                        onMouseLeave={() => setHoveredNode(null)}
                        style={{
                          padding: "1.25rem 1.4rem",
                          background: hoveredNode === node.id ? `${layer.color}12` : "#0C0F16",
                          border: `1px solid ${hoveredNode === node.id ? layer.color + "50" : "#1E2230"}`,
                          borderRadius: "8px",
                          transition: "all 0.15s",
                          cursor: "default",
                        }}
                      >
                        <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", marginBottom: "0.5rem" }}>
                          <span style={{ fontSize: "1.1rem" }}>{node.icon}</span>
                          <span style={{ fontSize: "0.95rem", color: layer.color, fontWeight: "600" }}>{node.label}</span>
                        </div>
                        <div style={{ fontSize: "0.78rem", color: "#7A7670", lineHeight: 1.65 }}>{node.sub}</div>
                      </div>
                    ))}
                  </div>
                )}

                {/* Arrow between layers */}
                {li < layers.length - 1 && (
                  <div style={{ textAlign: "center", padding: "0.2rem 0", color: "#2A2E3E", fontSize: "1.2rem" }}>↓</div>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Flow summary */}
        <div style={{
          background: "#141720",
          border: "1px solid #1E2230",
          borderRadius: "12px",
          padding: "2rem",
          marginBottom: "2.5rem",
        }}>
          <div style={{ fontSize: "0.7rem", letterSpacing: "0.2em", color: "#5A5860", textTransform: "uppercase", marginBottom: "1.2rem" }}>
            Fluxo de dados — visão linear
          </div>
          <div style={{
            display: "flex", alignItems: "center", gap: "0",
            overflowX: "auto", padding: "0.5rem 0",
          }}>
            {[
              { label: "APIs & ZIPs", color: "#6C9BC7" },
              { label: "Prefect + Python", color: "#E8946A" },
              { label: "Bronze (raw)", color: "#8B7A50" },
              { label: "Silver (clean)", color: "#9CB8AA" },
              { label: "Gold (analytical)", color: "#C8A840" },
              { label: "DuckDB + dbt", color: "#B08FD4" },
              { label: "Superset / Jupyter", color: "#E87D7D" },
            ].map((step, i) => (
              <div key={i} style={{ display: "flex", alignItems: "center", flexShrink: 0 }}>
                <div style={{
                  padding: "0.5rem 1rem",
                  background: step.color + "18",
                  border: `1px solid ${step.color}50`,
                  borderRadius: "6px",
                  fontSize: "0.75rem",
                  color: step.color,
                  fontFamily: "monospace",
                  whiteSpace: "nowrap",
                }}>{step.label}</div>
                {i < 6 && <div style={{ color: "#2A2E3E", padding: "0 0.3rem", fontSize: "1rem" }}>→</div>}
              </div>
            ))}
          </div>
        </div>

        {/* Princípios */}
        <div style={{ marginBottom: "2.5rem" }}>
          <div style={{ fontSize: "0.7rem", letterSpacing: "0.2em", color: "#5A5860", textTransform: "uppercase", marginBottom: "1.2rem" }}>
            Princípios arquiteturais críticos
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: "1rem" }}>
            {principles.map((p, i) => (
              <div key={i} style={{
                padding: "1.25rem",
                background: "#0C0F16",
                border: "1px solid #1E2230",
                borderRadius: "8px",
              }}>
                <div style={{ fontSize: "1.3rem", marginBottom: "0.5rem" }}>{p.icon}</div>
                <div style={{ fontSize: "0.9rem", color: "#D8D4CC", fontWeight: "600", marginBottom: "0.4rem" }}>{p.title}</div>
                <div style={{ fontSize: "0.78rem", color: "#6A6660", lineHeight: 1.65 }}>{p.desc}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Stack tecnológico */}
        <div style={{
          background: "#141720",
          border: "1px solid #1E2230",
          borderRadius: "12px",
          padding: "2rem",
          marginBottom: "2.5rem",
        }}>
          <div style={{ fontSize: "0.7rem", letterSpacing: "0.2em", color: "#5A5860", textTransform: "uppercase", marginBottom: "1.5rem" }}>
            Stack tecnológico completo — todas as ferramentas open source
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "1.5rem" }}>
            {[
              { cat: "Orquestração", items: ["Prefect 3", "docker-compose"] },
              { cat: "Ingestão Python", items: ["requests / httpx", "pyarrow", "sidrapy", "wbdata", "pyreadstat"] },
              { cat: "Ingestão R", items: ["EdSurvey", "intsvy", "sidrar", "eurostat", "WDI"] },
              { cat: "Armazenamento", items: ["Delta Lake", "Apache Parquet", "PostgreSQL 16"] },
              { cat: "Processamento", items: ["DuckDB 1.x", "dbt Core", "pandas / polars"] },
              { cat: "Governança", items: ["OpenMetadata", "Great Expectations", "Git + DVC"] },
              { cat: "Visualização", items: ["Apache Superset", "JupyterLab", "Quarto"] },
              { cat: "ML (opcional)", items: ["scikit-learn", "MLflow", "statsmodels"] },
            ].map(group => (
              <div key={group.cat}>
                <div style={{ fontSize: "0.65rem", color: "#6C9BC7", letterSpacing: "0.15em", textTransform: "uppercase", marginBottom: "0.6rem" }}>
                  {group.cat}
                </div>
                {group.items.map(item => (
                  <div key={item} style={{
                    fontSize: "0.8rem", color: "#8A8680",
                    padding: "0.2rem 0",
                    borderBottom: "1px solid #1A1E2A",
                    fontFamily: "monospace",
                  }}>{item}</div>
                ))}
              </div>
            ))}
          </div>
        </div>

        {/* Requisitos de hardware */}
        <div style={{
          background: "linear-gradient(135deg, #141A10 0%, #0F1117 100%)",
          border: "1px solid #2A3A20",
          borderRadius: "12px",
          padding: "1.75rem 2rem",
        }}>
          <div style={{ fontSize: "0.7rem", letterSpacing: "0.2em", color: "#7CB99A", textTransform: "uppercase", marginBottom: "1.2rem" }}>
            Requisitos mínimos de hardware on-premise
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "1.5rem" }}>
            {[
              { label: "RAM", min: "16 GB", rec: "32 GB", note: "DuckDB usa memória agressivamente" },
              { label: "CPU", min: "4 cores", rec: "8+ cores", note: "Paralelo no DuckDB" },
              { label: "Armazenamento", min: "500 GB SSD", rec: "1–2 TB SSD", note: "Parquet comprime ~5–10×" },
              { label: "SO", min: "Ubuntu 22.04 LTS", rec: "Ubuntu 22.04 LTS", note: "Docker nativo, suporte longo" },
            ].map(hw => (
              <div key={hw.label}>
                <div style={{ fontSize: "0.65rem", color: "#5A5860", textTransform: "uppercase", letterSpacing: "0.1em" }}>{hw.label}</div>
                <div style={{ fontSize: "0.9rem", color: "#7CB99A", marginTop: "0.2rem" }}>mín: <strong>{hw.min}</strong></div>
                <div style={{ fontSize: "0.9rem", color: "#A8D8B8" }}>rec: <strong>{hw.rec}</strong></div>
                <div style={{ fontSize: "0.7rem", color: "#4A5A4A", marginTop: "0.3rem" }}>{hw.note}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Footer */}
        <div style={{ textAlign: "center", padding: "2rem 0 1rem", color: "#3A3830", fontSize: "0.75rem" }}>
          Arquitetura Data Lakehouse Educacional · Medallion Pattern · On-premise · Open Source
        </div>
      </div>

      <style>{`
        @keyframes fadeIn { from { opacity: 0; transform: translateY(-4px); } to { opacity: 1; transform: translateY(0); } }
        * { box-sizing: border-box; }
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: #0F1117; }
        ::-webkit-scrollbar-thumb { background: #2A2E3E; border-radius: 3px; }
      `}</style>
    </div>
  );
}
