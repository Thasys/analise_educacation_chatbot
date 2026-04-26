import { useState } from "react";

const BG = "#080A10";
const SURFACE = "#0E1220";
const BORDER = "#1E2438";
const ACCENT = "#A8C5E8";

export default function FrontendArch() {
  const [tab, setTab] = useState("layout");
  const [hoveredZone, setHoveredZone] = useState(null);
  const [flowStep, setFlowStep] = useState(0);

  return (
    <div style={{ fontFamily: "'Georgia', serif", background: BG, minHeight: "100vh", color: "#E0DDD8" }}>

      {/* Header */}
      <div style={{
        background: "linear-gradient(135deg, #0F1528 0%, #080A10 100%)",
        borderBottom: `1px solid ${BORDER}`,
        padding: "2.5rem 2.5rem 1.8rem",
        position: "relative", overflow: "hidden",
      }}>
        <div style={{
          position: "absolute", inset: 0,
          background: "radial-gradient(ellipse at 20% 50%, rgba(168,197,232,0.05) 0%, transparent 60%)",
          pointerEvents: "none",
        }} />
        <div style={{ fontSize: "0.65rem", letterSpacing: "0.25em", color: ACCENT, marginBottom: "0.5rem", textTransform: "uppercase" }}>
          Frontend & Integração · Parte 3 de 3
        </div>
        <h1 style={{ fontSize: "clamp(1.5rem, 2.5vw, 2.2rem)", margin: 0, fontWeight: 400, color: "#F0EDE6", letterSpacing: "-0.02em" }}>
          Interface Unificada & Camada de Integração
        </h1>
        <p style={{ margin: "0.6rem 0 0", color: "#6A6660", fontSize: "0.88rem", maxWidth: "640px", lineHeight: 1.6 }}>
          Next.js 14 · FastAPI Gateway · SSE Streaming · Workspace único com chat, dashboards, explorador e citações
        </p>
      </div>

      {/* Tabs */}
      <div style={{ background: SURFACE, borderBottom: `1px solid ${BORDER}`, padding: "0 2.5rem", display: "flex", gap: "0", overflowX: "auto" }}>
        {[
          { id: "layout", label: "Layout da Interface" },
          { id: "stack", label: "Stack Tecnológico" },
          { id: "integration", label: "Pontos de Integração" },
          { id: "flow", label: "Jornada do Usuário" },
        ].map(t => (
          <button key={t.id} onClick={() => setTab(t.id)} style={{
            background: "none", border: "none", cursor: "pointer",
            padding: "1rem 1.2rem", whiteSpace: "nowrap",
            color: tab === t.id ? ACCENT : "#5A5860",
            borderBottom: `2px solid ${tab === t.id ? ACCENT : "transparent"}`,
            fontSize: "0.82rem", letterSpacing: "0.05em", fontFamily: "inherit",
            transition: "color 0.15s",
          }}>{t.label}</button>
        ))}
      </div>

      <div style={{ padding: "2rem 2.5rem", maxWidth: "1280px", margin: "0 auto" }}>

        {tab === "layout" && (
          <div>
            <div style={{ fontSize: "0.65rem", color: "#5A5860", letterSpacing: "0.2em", textTransform: "uppercase", marginBottom: "1rem" }}>
              Wireframe · Passe o mouse sobre cada zona
            </div>

            <div style={{
              background: "#050608", border: `1px solid ${BORDER}`,
              borderRadius: "12px", overflow: "hidden", marginBottom: "1.5rem",
            }}>
              <div style={{
                background: "#0B0D14", padding: "0.7rem 1rem",
                borderBottom: `1px solid ${BORDER}`,
                display: "flex", alignItems: "center", gap: "0.5rem",
              }}>
                <div style={{ display: "flex", gap: "0.4rem" }}>
                  {[1,2,3].map(i => <span key={i} style={{ width: 10, height: 10, borderRadius: "50%", background: "#3A3A3A" }} />)}
                </div>
                <div style={{
                  flex: 1, background: "#05070B", padding: "0.25rem 0.8rem",
                  borderRadius: "4px", fontSize: "0.7rem", color: "#4A4848",
                  fontFamily: "monospace",
                }}>http://localhost:3000/compare</div>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "240px 1fr 280px", minHeight: "520px" }}>
                <div
                  onMouseEnter={() => setHoveredZone("sidebar")}
                  onMouseLeave={() => setHoveredZone(null)}
                  style={{
                    background: hoveredZone === "sidebar" ? "#101728" : "#0A0D18",
                    borderRight: `1px solid ${BORDER}`,
                    padding: "1rem 0.9rem", transition: "background 0.15s", cursor: "pointer",
                  }}
                >
                  <div style={{ fontSize: "0.6rem", color: "#6C9BC7", letterSpacing: "0.2em", textTransform: "uppercase", marginBottom: "0.8rem", padding: "0 0.4rem" }}>
                    ① Navigation
                  </div>
                  {["🆕 Nova conversa", "📊 Dashboards", "🔎 Explorador", "📚 Biblioteca", "⚙️ Configurações"].map(item => (
                    <div key={item} style={{
                      padding: "0.5rem 0.6rem", fontSize: "0.77rem",
                      color: "#8A8680", borderRadius: "4px", marginBottom: "0.2rem",
                    }}>{item}</div>
                  ))}
                  <div style={{ marginTop: "1.5rem", fontSize: "0.6rem", color: "#4A4848", letterSpacing: "0.15em", textTransform: "uppercase", padding: "0 0.4rem", marginBottom: "0.5rem" }}>
                    Histórico recente
                  </div>
                  {["PISA 2022 vs Brasil", "IDEB por região", "Investimento educação"].map(item => (
                    <div key={item} style={{
                      padding: "0.45rem 0.6rem", fontSize: "0.72rem",
                      color: "#5A5860", fontFamily: "monospace",
                      whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis",
                    }}>{item}</div>
                  ))}
                </div>

                <div
                  onMouseEnter={() => setHoveredZone("workspace")}
                  onMouseLeave={() => setHoveredZone(null)}
                  style={{
                    background: hoveredZone === "workspace" ? "#0A0D18" : "#05070B",
                    padding: "1.2rem 1.3rem", transition: "background 0.15s", cursor: "pointer",
                    display: "flex", flexDirection: "column", gap: "0.8rem",
                  }}
                >
                  <div style={{ fontSize: "0.6rem", color: "#88C5A8", letterSpacing: "0.2em", textTransform: "uppercase" }}>
                    ② Workspace · Chat + Visualizações
                  </div>

                  <div style={{ background: "#0E1220", padding: "0.8rem 1rem", borderRadius: "8px", border: "1px solid #1A2030" }}>
                    <div style={{ fontSize: "0.65rem", color: "#6C9BC7", marginBottom: "0.3rem" }}>Você</div>
                    <div style={{ fontSize: "0.78rem", color: "#A0A098", lineHeight: 1.5 }}>
                      Compare o desempenho em matemática PISA 2022 entre Brasil e países nórdicos
                    </div>
                  </div>

                  <div style={{ background: "#0A0D18", padding: "0.6rem 0.85rem", borderRadius: "6px", border: "1px dashed #253048" }}>
                    <div style={{ fontSize: "0.62rem", color: "#B08FD4", marginBottom: "0.2rem", fontFamily: "monospace" }}>
                      ● agents thinking...
                    </div>
                    <div style={{ fontSize: "0.7rem", color: "#5A5860", fontFamily: "monospace" }}>
                      ✓ Profiler → intenção: comparação numérica<br/>
                      ✓ Retriever → DuckDB query Gold.pisa_results<br/>
                      ⟳ Statistician → aplicando BRR weights...
                    </div>
                  </div>

                  <div style={{ background: "#0E1220", padding: "0.8rem 1rem", borderRadius: "8px", border: "1px solid #1A2030" }}>
                    <div style={{ fontSize: "0.65rem", color: "#88C5A8", marginBottom: "0.4rem" }}>Assistente</div>
                    <div style={{ fontSize: "0.75rem", color: "#A0A098", lineHeight: 1.55, marginBottom: "0.7rem" }}>
                      Em matemática PISA 2022, Brasil obteve 379 pontos enquanto a Finlândia alcançou 484...
                    </div>

                    <div style={{
                      background: "#050608", borderRadius: "6px",
                      padding: "0.8rem", height: "110px",
                      border: "1px solid #141828",
                    }}>
                      <div style={{ fontSize: "0.6rem", color: "#D4A04A", marginBottom: "0.4rem" }}>📊 PISA Math 2022 · Brasil vs Nórdicos</div>
                      <div style={{ display: "flex", alignItems: "flex-end", gap: "0.4rem", height: "70px" }}>
                        {[
                          { l: "BR", h: 40, c: "#E87D7D" },
                          { l: "FI", h: 72, c: "#88C5A8" },
                          { l: "DK", h: 66, c: "#88C5A8" },
                          { l: "SE", h: 68, c: "#88C5A8" },
                          { l: "NO", h: 62, c: "#88C5A8" },
                        ].map(b => (
                          <div key={b.l} style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", gap: "0.2rem" }}>
                            <div style={{ width: "100%", height: `${b.h}%`, background: b.c, opacity: 0.7, borderRadius: "2px 2px 0 0" }} />
                            <div style={{ fontSize: "0.55rem", color: "#6A6660", fontFamily: "monospace" }}>{b.l}</div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>

                  <div style={{ marginTop: "auto", background: "#0E1220", padding: "0.65rem 0.9rem", borderRadius: "8px", border: "1px solid #253048", display: "flex", alignItems: "center", gap: "0.5rem" }}>
                    <div style={{ flex: 1, fontSize: "0.72rem", color: "#3A3838", fontStyle: "italic" }}>Faça uma pergunta sobre educação comparada...</div>
                    <div style={{ color: ACCENT, fontSize: "0.9rem" }}>↗</div>
                  </div>
                </div>

                <div
                  onMouseEnter={() => setHoveredZone("context")}
                  onMouseLeave={() => setHoveredZone(null)}
                  style={{
                    background: hoveredZone === "context" ? "#101728" : "#0A0D18",
                    borderLeft: `1px solid ${BORDER}`,
                    padding: "1rem 0.9rem", transition: "background 0.15s", cursor: "pointer",
                  }}
                >
                  <div style={{ fontSize: "0.6rem", color: "#E87D7D", letterSpacing: "0.2em", textTransform: "uppercase", marginBottom: "0.8rem" }}>
                    ③ Context Panel
                  </div>
                  <div style={{ fontSize: "0.65rem", color: "#5A5860", marginBottom: "0.5rem", textTransform: "uppercase", letterSpacing: "0.1em" }}>Fontes usadas</div>
                  {[
                    { s: "OECD PISA 2022", c: "#D4A04A" },
                    { s: "INEP SAEB 2023", c: "#7CB99A" },
                    { s: "UNESCO UIS", c: "#6C9BC7" },
                  ].map(f => (
                    <div key={f.s} style={{
                      padding: "0.4rem 0.5rem", fontSize: "0.7rem",
                      color: f.c, borderLeft: `2px solid ${f.c}`,
                      background: "#080B14", marginBottom: "0.3rem",
                      fontFamily: "monospace",
                    }}>{f.s}</div>
                  ))}

                  <div style={{ marginTop: "1.2rem", fontSize: "0.65rem", color: "#5A5860", marginBottom: "0.5rem", textTransform: "uppercase", letterSpacing: "0.1em" }}>Citações</div>
                  {["Schleicher (2019)", "Carnoy et al. (2015)", "OECD (2023)"].map(c => (
                    <div key={c} style={{
                      padding: "0.35rem 0", fontSize: "0.7rem",
                      color: "#7A7670", borderBottom: "1px solid #141828",
                    }}>📎 {c}</div>
                  ))}

                  <div style={{ marginTop: "1.2rem", fontSize: "0.65rem", color: "#5A5860", marginBottom: "0.5rem", textTransform: "uppercase", letterSpacing: "0.1em" }}>Query SQL</div>
                  <div style={{
                    fontSize: "0.62rem", color: "#88C5A8",
                    fontFamily: "monospace", background: "#050608",
                    padding: "0.5rem", borderRadius: "4px",
                    lineHeight: 1.5, border: "1px solid #141828",
                  }}>SELECT country, math_mean<br/>FROM pisa_2022<br/>WHERE iso IN (...)</div>

                  <button style={{
                    marginTop: "0.6rem", width: "100%",
                    background: "#101728", border: `1px solid ${BORDER}`,
                    color: "#7A7670", padding: "0.4rem",
                    fontSize: "0.65rem", borderRadius: "4px",
                    cursor: "pointer", fontFamily: "inherit",
                  }}>⬇ Exportar CSV</button>
                </div>
              </div>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "1rem" }}>
              {[
                {
                  num: "①", label: "Navigation", color: "#6C9BC7",
                  desc: "Histórico de conversas, acesso a dashboards Superset embutidos, explorador de dados da Gold Layer e biblioteca de referências. Colapsável em telas menores.",
                  components: ["Sheet", "ScrollArea", "Command", "Breadcrumb"],
                },
                {
                  num: "②", label: "Workspace", color: "#88C5A8",
                  desc: "Chat principal com streaming SSE. Renderiza mensagens em Markdown, exibe reasoning dos agentes em tempo real, incorpora gráficos Plotly inline e permite follow-up contextual.",
                  components: ["Chat", "Plotly", "Markdown", "MermaidJS"],
                },
                {
                  num: "③", label: "Context Panel", color: "#E87D7D",
                  desc: "Transparência total: mostra quais fontes foram consultadas, referências acadêmicas recuperadas pelo RAG, SQL executado no DuckDB e opções de exportação do resultado.",
                  components: ["Popover", "Collapsible", "Badge", "CodeBlock"],
                },
              ].map(zone => (
                <div key={zone.label} style={{
                  padding: "1.1rem 1.25rem", background: SURFACE,
                  border: `1px solid ${zone.color}40`,
                  borderTop: `2px solid ${zone.color}`, borderRadius: "8px",
                }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.5rem" }}>
                    <span style={{ color: zone.color, fontSize: "1rem" }}>{zone.num}</span>
                    <span style={{ fontSize: "0.85rem", color: zone.color, fontWeight: 600 }}>{zone.label}</span>
                  </div>
                  <div style={{ fontSize: "0.76rem", color: "#7A7670", lineHeight: 1.6, marginBottom: "0.7rem" }}>{zone.desc}</div>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "0.3rem" }}>
                    {zone.components.map(c => (
                      <span key={c} style={{
                        padding: "0.15rem 0.45rem", borderRadius: "3px",
                        background: "#0A0D18", color: "#6A6660",
                        fontSize: "0.65rem", fontFamily: "monospace",
                        border: "1px solid #1A2030",
                      }}>{c}</span>
                    ))}
                  </div>
                </div>
              ))}
            </div>

            <div style={{
              marginTop: "1.5rem", padding: "1.4rem 1.6rem",
              background: "linear-gradient(135deg, #151028 0%, #080A10 100%)",
              border: "1px solid #2A2040", borderRadius: "10px",
            }}>
              <div style={{ fontSize: "0.7rem", color: "#C8A0D8", textTransform: "uppercase", letterSpacing: "0.15em", marginBottom: "1rem" }}>
                Adaptação automática por perfil detectado
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "1rem" }}>
                {[
                  { p: "Pesquisador", det: "linguagem técnica, metodologia, referências específicas", ui: "SQL visível · ICs 95% · DOIs expandidos · export SPSS/R", icon: "🎓" },
                  { p: "Gestor Público", det: "vocabulário de políticas, regiões, metas do PNE", ui: "Gráficos simplificados · recortes territoriais · cards de alerta", icon: "🏛️" },
                  { p: "Estudante", det: "perguntas abertas, curiosidade, contexto histórico", ui: "Glossário inline · analogias · sugestões de próxima pergunta", icon: "📖" },
                ].map(prof => (
                  <div key={prof.p} style={{ padding: "0.9rem", background: "#0A0D18", borderRadius: "8px" }}>
                    <div style={{ fontSize: "1.3rem", marginBottom: "0.4rem" }}>{prof.icon}</div>
                    <div style={{ fontSize: "0.85rem", color: "#C8A0D8", fontWeight: 600, marginBottom: "0.4rem" }}>{prof.p}</div>
                    <div style={{ fontSize: "0.7rem", color: "#5A5860", fontStyle: "italic", marginBottom: "0.5rem", lineHeight: 1.5 }}>
                      Detecta: {prof.det}
                    </div>
                    <div style={{ fontSize: "0.72rem", color: "#A0A098", lineHeight: 1.5 }}>{prof.ui}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {tab === "stack" && (
          <div>
            <div style={{ marginBottom: "2rem" }}>
              <div style={{ fontSize: "0.65rem", color: "#5A5860", letterSpacing: "0.2em", textTransform: "uppercase", marginBottom: "1rem" }}>
                Frontend · Stack Principal
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: "0.9rem" }}>
                {[
                  { tech: "Next.js 14", sub: "App Router · Server Components", why: "SSR para SEO interno, rotas paralelas para chat + dashboards, streaming nativo de respostas LLM via RSC.", color: "#A8C5E8" },
                  { tech: "TypeScript 5", sub: "Strict mode", why: "Tipagem end-to-end com o FastAPI (via openapi-typescript). Zero erros de runtime em produção acadêmica.", color: "#6C9BC7" },
                  { tech: "Tailwind CSS 4", sub: "Design tokens", why: "Produtividade máxima para solo dev. Zero CSS customizado, zero JS runtime para estilos.", color: "#88C5A8" },
                  { tech: "shadcn/ui", sub: "Radix + Tailwind", why: "Componentes acessíveis copy-paste, totalmente customizáveis. 50+ componentes prontos (Dialog, Command, Sheet, Chart).", color: "#D4A04A" },
                  { tech: "Vercel AI SDK", sub: "useChat() + streaming", why: "Hook pronto para SSE streaming do LLM. Integra nativamente com FastAPI e CrewAI via endpoints compatíveis.", color: "#C8A0D8" },
                  { tech: "TanStack Query", sub: "React Query v5", why: "Cache inteligente de consultas ao Lakehouse. Deduplicação de requests, revalidação em foco, mutações otimistas.", color: "#E87D7D" },
                  { tech: "Plotly.js", sub: "via react-plotly.js", why: "Gráficos interativos gerados pelos agentes. Zoom, export PNG/SVG, tooltips ricos. Alternativa: Recharts p/ simples.", color: "#E8946A" },
                  { tech: "Zustand", sub: "state management", why: "Store leve para estado de UI (perfil detectado, tema, painel ativo). Mais simples que Redux para projeto solo.", color: "#7CB99A" },
                ].map(item => (
                  <div key={item.tech} style={{
                    padding: "1.1rem 1.25rem", background: SURFACE,
                    border: `1px solid ${BORDER}`,
                    borderLeft: `3px solid ${item.color}`, borderRadius: "8px",
                  }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: "0.2rem" }}>
                      <span style={{ fontSize: "0.95rem", color: item.color, fontWeight: 600 }}>{item.tech}</span>
                      <span style={{ fontSize: "0.62rem", color: "#5A5860", fontFamily: "monospace" }}>{item.sub}</span>
                    </div>
                    <div style={{ fontSize: "0.76rem", color: "#7A7670", lineHeight: 1.6, marginTop: "0.5rem" }}>{item.why}</div>
                  </div>
                ))}
              </div>
            </div>

            <div style={{ marginBottom: "2rem" }}>
              <div style={{ fontSize: "0.65rem", color: "#5A5860", letterSpacing: "0.2em", textTransform: "uppercase", marginBottom: "1rem" }}>
                Backend Gateway · FastAPI unificado
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: "0.9rem" }}>
                {[
                  { tech: "FastAPI 0.110+", sub: "Python 3.11+", why: "Gateway único entre frontend e (CrewAI + Lakehouse). Validação Pydantic, docs OpenAPI automáticas, async nativo.", color: "#7CB99A" },
                  { tech: "SSE (EventSource)", sub: "streaming", why: "Server-Sent Events para streaming de respostas LLM e progresso dos agentes. Mais simples que WebSocket para one-way.", color: "#88C5A8" },
                  { tech: "WebSocket", sub: "opcional", why: "Para features bidirecionais como cancelamento de tarefa longa ou colaboração. Use SSE como padrão, WS só quando necessário.", color: "#6C9BC7" },
                  { tech: "Pydantic v2", sub: "validação", why: "Schemas compartilhados. Com openapi-typescript, o frontend recebe tipos gerados automaticamente do backend.", color: "#D4A04A" },
                  { tech: "SlowAPI", sub: "rate limiting", why: "Limita requests por IP. Previne abuso mesmo em rede interna (ex: usuário testando loop infinito).", color: "#E8946A" },
                  { tech: "Uvicorn + Gunicorn", sub: "ASGI server", why: "Uvicorn para desenvolvimento, Gunicorn+UvicornWorker para produção. 2-4 workers suficientes para uso acadêmico.", color: "#B08FD4" },
                ].map(item => (
                  <div key={item.tech} style={{
                    padding: "1.1rem 1.25rem", background: SURFACE,
                    border: `1px solid ${BORDER}`,
                    borderLeft: `3px solid ${item.color}`, borderRadius: "8px",
                  }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: "0.2rem" }}>
                      <span style={{ fontSize: "0.95rem", color: item.color, fontWeight: 600 }}>{item.tech}</span>
                      <span style={{ fontSize: "0.62rem", color: "#5A5860", fontFamily: "monospace" }}>{item.sub}</span>
                    </div>
                    <div style={{ fontSize: "0.76rem", color: "#7A7670", lineHeight: 1.6, marginTop: "0.5rem" }}>{item.why}</div>
                  </div>
                ))}
              </div>
            </div>

            <div style={{ marginBottom: "1.5rem" }}>
              <div style={{ fontSize: "0.65rem", color: "#5A5860", letterSpacing: "0.2em", textTransform: "uppercase", marginBottom: "1rem" }}>
                Deploy & Operação local
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: "0.9rem" }}>
                {[
                  { tech: "Docker Compose", sub: "orquestração", why: "Um único `docker-compose up` sobe: Next.js, FastAPI, DuckDB, Postgres, ChromaDB, Prefect, Superset.", color: "#A8C5E8" },
                  { tech: "Caddy (opcional)", sub: "reverse proxy", why: "Proxy reverso com HTTPS automático mesmo em rede interna. Alternativa mais simples que Nginx.", color: "#7CB99A" },
                  { tech: "Traefik", sub: "service discovery", why: "Alternativa ao Caddy se quiser roteamento dinâmico. Integra-se automaticamente com Docker Compose.", color: "#C8A0D8" },
                  { tech: "Git + Gitea", sub: "versionamento", why: "Versione infraestrutura (docker-compose.yml), prompts dos agentes, schemas dbt — tudo auditável.", color: "#88C5A8" },
                ].map(item => (
                  <div key={item.tech} style={{
                    padding: "1rem 1.2rem", background: SURFACE,
                    border: `1px solid ${BORDER}`,
                    borderLeft: `3px solid ${item.color}`, borderRadius: "8px",
                  }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: "0.2rem" }}>
                      <span style={{ fontSize: "0.9rem", color: item.color, fontWeight: 600 }}>{item.tech}</span>
                      <span style={{ fontSize: "0.6rem", color: "#5A5860", fontFamily: "monospace" }}>{item.sub}</span>
                    </div>
                    <div style={{ fontSize: "0.74rem", color: "#7A7670", lineHeight: 1.6, marginTop: "0.4rem" }}>{item.why}</div>
                  </div>
                ))}
              </div>
            </div>

            <div style={{
              padding: "1.4rem 1.6rem",
              background: "linear-gradient(135deg, #1A1410 0%, #080A10 100%)",
              border: "1px solid #302418", borderRadius: "10px",
            }}>
              <div style={{ fontSize: "0.7rem", color: "#E8946A", textTransform: "uppercase", letterSpacing: "0.15em", marginBottom: "1rem" }}>
                Por que NÃO usamos estas alternativas
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: "1rem" }}>
                {[
                  { name: "Streamlit", why: "Limitado para UIs complexas, re-executa todo o script a cada interação, difícil para chat em tempo real e multi-panel." },
                  { name: "Chainlit sozinho", why: "Ótimo para chat puro, mas insuficiente para dashboards embutidos e exploração de dados estilo BI." },
                  { name: "Gradio", why: "Projetado para demos ML, não para aplicações com múltiplas áreas funcionais integradas." },
                  { name: "Reflex (Python)", why: "Viável como fallback Python-only, mas performance e customização ficam abaixo de Next.js." },
                  { name: "Clerk/Auth0", why: "Auth externa é overkill para rede interna — use NextAuth com JWT simples ou auth por cabeçalho HTTP." },
                  { name: "Superset standalone", why: "Excelente embutido via iframe/SDK, mas não substitui chat conversacional como interface primária." },
                ].map(alt => (
                  <div key={alt.name} style={{ padding: "0.8rem", background: "#0A0D18", borderRadius: "6px" }}>
                    <div style={{ fontSize: "0.78rem", color: "#E8946A", fontWeight: 600, marginBottom: "0.3rem" }}>⌯ {alt.name}</div>
                    <div style={{ fontSize: "0.72rem", color: "#7A7670", lineHeight: 1.55 }}>{alt.why}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {tab === "integration" && (
          <div>
            <div style={{ marginBottom: "2rem" }}>
              <div style={{ fontSize: "0.65rem", color: "#5A5860", letterSpacing: "0.2em", textTransform: "uppercase", marginBottom: "1rem" }}>
                Diagrama de Integração · 4 camadas conectadas
              </div>
              <div style={{
                background: SURFACE, border: `1px solid ${BORDER}`,
                borderRadius: "12px", padding: "2rem",
              }}>
                <div style={{ display: "flex", flexDirection: "column", gap: "0.3rem" }}>
                  {[
                    { name: "Browser · Next.js 14", port: "3000", color: "#A8C5E8", items: ["UI / Chat / Dashboards"] },
                    { name: "FastAPI Gateway", port: "8000", color: "#7CB99A", items: ["REST endpoints", "SSE streaming", "WebSocket (opcional)"] },
                    { name: "Serviços Internos", port: "—", color: "#B08FD4", items: ["CrewAI Agents", "DuckDB (embedded)", "ChromaDB (embedded)"] },
                    { name: "Data Layer", port: "5432 / disk", color: "#D4A04A", items: ["PostgreSQL (metadados)", "Delta Lake", "Parquet files (Bronze/Silver/Gold)"] },
                  ].map((layer, i, arr) => (
                    <div key={layer.name}>
                      <div style={{
                        padding: "1rem 1.3rem",
                        background: `${layer.color}10`,
                        border: `1px solid ${layer.color}40`,
                        borderRadius: "8px",
                        display: "grid", gridTemplateColumns: "200px 80px 1fr",
                        alignItems: "center", gap: "1rem",
                      }}>
                        <div style={{ fontSize: "0.88rem", color: layer.color, fontWeight: 600 }}>{layer.name}</div>
                        <div style={{ fontSize: "0.7rem", color: "#5A5860", fontFamily: "monospace" }}>:{layer.port}</div>
                        <div style={{ display: "flex", flexWrap: "wrap", gap: "0.4rem" }}>
                          {layer.items.map(item => (
                            <span key={item} style={{
                              padding: "0.2rem 0.55rem",
                              background: "#080B14", color: "#8A8680",
                              fontSize: "0.7rem", fontFamily: "monospace",
                              borderRadius: "4px", border: `1px solid ${BORDER}`,
                            }}>{item}</span>
                          ))}
                        </div>
                      </div>
                      {i < arr.length - 1 && (
                        <div style={{ textAlign: "center", padding: "0.2rem 0", color: "#2A2E3E" }}>↕</div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div style={{ marginBottom: "2rem" }}>
              <div style={{ fontSize: "0.65rem", color: "#5A5860", letterSpacing: "0.2em", textTransform: "uppercase", marginBottom: "1rem" }}>
                Contrato de API · FastAPI endpoints
              </div>
              <div style={{
                background: "#050608", border: `1px solid ${BORDER}`,
                borderRadius: "10px", overflow: "hidden",
              }}>
                {[
                  { method: "POST", path: "/api/chat/stream", desc: "Envia pergunta do usuário, retorna SSE stream com chunks da resposta", color: "#88C5A8" },
                  { method: "GET", path: "/api/chat/:id/reasoning", desc: "SSE com progresso dos agentes (Profiler → Retriever → etc)", color: "#88C5A8" },
                  { method: "GET", path: "/api/data/catalog", desc: "Lista datasets disponíveis na Gold Layer (integra com OpenMetadata)", color: "#D4A04A" },
                  { method: "POST", path: "/api/data/query", desc: "Executa query pré-validada no DuckDB, retorna JSON/CSV", color: "#D4A04A" },
                  { method: "GET", path: "/api/data/:dataset/preview", desc: "Amostra 100 linhas de um dataset para o explorador", color: "#D4A04A" },
                  { method: "POST", path: "/api/rag/search", desc: "Busca semântica no ChromaDB, retorna artigos relevantes com scores", color: "#E87D7D" },
                  { method: "GET", path: "/api/rag/citation/:doi", desc: "Resolve DOI e retorna metadados formatados em ABNT/APA", color: "#E87D7D" },
                  { method: "POST", path: "/api/viz/generate", desc: "Gera Plotly JSON spec a partir de dataset + tipo de chart", color: "#C8A0D8" },
                  { method: "GET", path: "/api/health", desc: "Health check de todos os serviços (DuckDB, ChromaDB, CrewAI, Postgres)", color: "#6C9BC7" },
                  { method: "GET", path: "/api/profile/detect", desc: "Classifica perfil do usuário com base no histórico da sessão", color: "#6C9BC7" },
                ].map((ep, i, arr) => (
                  <div key={ep.path} style={{
                    display: "grid", gridTemplateColumns: "80px 280px 1fr",
                    gap: "1rem", padding: "0.7rem 1.2rem",
                    borderBottom: i < arr.length - 1 ? `1px solid ${BORDER}` : "none",
                    alignItems: "center",
                  }}>
                    <span style={{
                      fontSize: "0.65rem", fontFamily: "monospace",
                      color: ep.color, letterSpacing: "0.05em",
                      padding: "0.15rem 0.4rem", borderRadius: "3px",
                      background: ep.color + "15", textAlign: "center",
                    }}>{ep.method}</span>
                    <span style={{ fontFamily: "monospace", fontSize: "0.78rem", color: "#A8C5E8" }}>{ep.path}</span>
                    <span style={{ fontSize: "0.73rem", color: "#7A7670", lineHeight: 1.5 }}>{ep.desc}</span>
                  </div>
                ))}
              </div>
            </div>

            <div style={{ marginBottom: "1.5rem" }}>
              <div style={{ fontSize: "0.65rem", color: "#5A5860", letterSpacing: "0.2em", textTransform: "uppercase", marginBottom: "1rem" }}>
                Padrões de comunicação por tipo de operação
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "0.9rem" }}>
                {[
                  { name: "REST síncrono", use: "Consultas rápidas: catálogo, preview, health check, busca RAG", color: "#6C9BC7", ex: "GET /api/data/catalog → 200ms" },
                  { name: "Server-Sent Events", use: "Streaming de resposta do LLM + progresso dos agentes em tempo real", color: "#88C5A8", ex: "POST /api/chat/stream → chunks contínuos" },
                  { name: "WebSocket", use: "Quando precisar bidirecional: cancelamento, notificações push", color: "#B08FD4", ex: "ws://.../agent-control" },
                  { name: "Background Jobs", use: "Tarefas longas: re-indexação RAG, refresh da Gold Layer, treino de modelo", color: "#D4A04A", ex: "Prefect schedule → task queue" },
                ].map(p => (
                  <div key={p.name} style={{
                    padding: "1rem 1.2rem", background: SURFACE,
                    border: `1px solid ${p.color}40`, borderRadius: "8px",
                  }}>
                    <div style={{ fontSize: "0.82rem", color: p.color, fontWeight: 600, marginBottom: "0.4rem" }}>{p.name}</div>
                    <div style={{ fontSize: "0.75rem", color: "#7A7670", lineHeight: 1.6, marginBottom: "0.5rem" }}>{p.use}</div>
                    <div style={{
                      fontFamily: "monospace", fontSize: "0.68rem",
                      color: p.color + "CC", background: "#050608",
                      padding: "0.3rem 0.5rem", borderRadius: "4px",
                    }}>{p.ex}</div>
                  </div>
                ))}
              </div>
            </div>

            <div style={{
              background: "linear-gradient(135deg, #0E1810 0%, #080A10 100%)",
              border: "1px solid #1E3020",
              borderRadius: "10px", padding: "1.4rem 1.6rem",
            }}>
              <div style={{ fontSize: "0.7rem", color: "#88C5A8", textTransform: "uppercase", letterSpacing: "0.15em", marginBottom: "0.7rem" }}>
                Exemplo · Streaming SSE com React puro (sem dependências externas)
              </div>
              <pre style={{
                fontFamily: "monospace", fontSize: "0.72rem",
                color: "#A8D8B8", lineHeight: 1.75, margin: 0,
                overflowX: "auto",
              }}>{`// app/api/chat/route.ts (Next.js App Router)
export async function POST(req) {
  const { message, profile } = await req.json();

  const response = await fetch("http://localhost:8000/api/chat/stream", {
    method: "POST",
    body: JSON.stringify({ message, profile }),
  });

  return new Response(response.body, {
    headers: { "Content-Type": "text/event-stream" },
  });
}

// components/Chat.tsx - React puro com SSE nativo
"use client";
import { useState } from "react";

export function Chat() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    let fullResponse = "";

    const eventSource = new EventSource(
      \`/api/chat?message=\${encodeURIComponent(input)}\`
    );

    eventSource.onmessage = (event) => {
      const chunk = JSON.parse(event.data).chunk;
      fullResponse += chunk;
      setMessages(prev => [...prev.slice(0, -1), 
        { role: "assistant", content: fullResponse }]);
    };

    eventSource.onerror = () => {
      eventSource.close();
      setLoading(false);
    };
  };

  return (/* render messages + input form */);
}`}</pre>
            </div>
          </div>
        )}

        {tab === "flow" && (
          <div>
            <div style={{ fontSize: "0.65rem", color: "#5A5860", letterSpacing: "0.2em", textTransform: "uppercase", marginBottom: "1rem" }}>
              Jornada completa · Pergunta do usuário até resposta renderizada
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "0.2rem", marginBottom: "2rem" }}>
              {[
                { t: "0ms", actor: "Usuário", action: "Digita: 'Compare PISA Matemática Brasil vs Finlândia 2022'", color: "#A8C5E8", layer: "Next.js UI" },
                { t: "+50ms", actor: "Next.js", action: "Captura input, adiciona ao Zustand store, envia POST /api/chat/stream", color: "#A8C5E8", layer: "Next.js → FastAPI" },
                { t: "+80ms", actor: "FastAPI", action: "Valida payload (Pydantic), abre SSE stream, encaminha para CrewAI Orchestrator", color: "#7CB99A", layer: "FastAPI Gateway" },
                { t: "+200ms", actor: "Orchestrator", action: "Decide: fluxo com dados. Aciona Profiler + Retriever + Statistician + Visualizer", color: "#E8946A", layer: "CrewAI" },
                { t: "+400ms", actor: "Profiler", action: "Classifica perfil: 'pesquisador'. Emite evento SSE para UI atualizar contexto", color: "#6C9BC7", layer: "CrewAI" },
                { t: "+800ms", actor: "Retriever", action: "Gera SQL, chama /api/data/query, DuckDB retorna DataFrame com scores", color: "#7CB99A", layer: "CrewAI → DuckDB" },
                { t: "+1.2s", actor: "Statistician", action: "Valida plausible values, calcula diferença significativa (105 pontos, p<.001)", color: "#B08FD4", layer: "CrewAI" },
                { t: "+2.0s", actor: "Comparativist", action: "Enriquece com contexto: Finlândia PISA desde 2000, diferenças institucionais", color: "#D4A04A", layer: "CrewAI" },
                { t: "+3.0s", actor: "Citation Agent", action: "RAG no ChromaDB: retorna Schleicher (2019), Carnoy et al. (2015), OECD (2023)", color: "#E87D7D", layer: "CrewAI → ChromaDB" },
                { t: "+4.0s", actor: "Visualizer", action: "Gera Plotly spec: bar chart BR vs FI com ICs 95%. Retorna JSON", color: "#88C5A8", layer: "CrewAI" },
                { t: "+5.0s", actor: "Synthesizer", action: "Combina tudo em Markdown adaptado ao perfil 'pesquisador'", color: "#C8A0D8", layer: "CrewAI" },
                { t: "+5.1s", actor: "FastAPI", action: "Envia chunks SSE conforme Synthesizer gera tokens", color: "#7CB99A", layer: "FastAPI → Next.js" },
                { t: "+5.2s", actor: "Next.js", action: "useChat() hook recebe stream, renderiza Markdown + Plotly incrementalmente", color: "#A8C5E8", layer: "Next.js UI" },
                { t: "+8.0s", actor: "Next.js", action: "Atualiza Context Panel (direito) com fontes, SQL usado e citações", color: "#A8C5E8", layer: "Next.js UI" },
                { t: "+8.1s", actor: "Usuário", action: "Lê resposta, clica em citação → abre modal com abstract do artigo", color: "#A8C5E8", layer: "Next.js UI" },
              ].map((step, i) => (
                <div key={i}
                  onMouseEnter={() => setFlowStep(i)}
                  style={{
                    display: "grid",
                    gridTemplateColumns: "70px 130px 1fr 180px",
                    gap: "1rem", padding: "0.7rem 1rem",
                    background: flowStep === i ? `${step.color}12` : SURFACE,
                    border: `1px solid ${flowStep === i ? step.color + "40" : BORDER}`,
                    borderLeft: `3px solid ${step.color}`, borderRadius: "6px",
                    alignItems: "center", cursor: "pointer",
                    transition: "all 0.15s",
                  }}
                >
                  <span style={{ fontFamily: "monospace", fontSize: "0.72rem", color: step.color }}>{step.t}</span>
                  <span style={{ fontSize: "0.78rem", color: step.color, fontWeight: 600 }}>{step.actor}</span>
                  <span style={{ fontSize: "0.76rem", color: "#A0A098", lineHeight: 1.5 }}>{step.action}</span>
                  <span style={{ fontSize: "0.68rem", color: "#5A5860", fontFamily: "monospace", textAlign: "right" }}>{step.layer}</span>
                </div>
              ))}
            </div>

            <div style={{
              padding: "1.4rem 1.6rem",
              background: "linear-gradient(135deg, #12182A 0%, #080A10 100%)",
              border: `1px solid ${BORDER}`, borderRadius: "10px",
              display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
              gap: "1.5rem",
            }}>
              {[
                { label: "Tempo até 1º token", val: "~1s", color: "#88C5A8" },
                { label: "Tempo até resposta completa", val: "~8s", color: "#A8C5E8" },
                { label: "Requests HTTP totais", val: "4", color: "#D4A04A" },
                { label: "Camadas atravessadas", val: "4", color: "#C8A0D8" },
                { label: "Tokens LLM consumidos", val: "~15k", color: "#E87D7D" },
              ].map(m => (
                <div key={m.label}>
                  <div style={{ fontSize: "0.65rem", color: "#5A5860", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: "0.3rem" }}>{m.label}</div>
                  <div style={{ fontSize: "1.4rem", color: m.color, fontWeight: 600, fontFamily: "monospace" }}>{m.val}</div>
                </div>
              ))}
            </div>

            <div style={{
              marginTop: "1.5rem", padding: "1.4rem 1.6rem",
              background: "linear-gradient(135deg, #0E1810 0%, #080A10 100%)",
              border: "1px solid #1E3020", borderRadius: "10px",
            }}>
              <div style={{ fontSize: "0.7rem", color: "#88C5A8", textTransform: "uppercase", letterSpacing: "0.15em", marginBottom: "0.6rem" }}>
                💡 Insight crítico de usabilidade
              </div>
              <div style={{ fontSize: "0.82rem", color: "#A0A098", lineHeight: 1.7 }}>
                O usuário vê a resposta começar a aparecer em ~1 segundo (primeiro token), mesmo que a resposta completa
                leve 8 segundos. Isso transforma a experiência: sem streaming, o usuário encararia uma tela de loading por
                8s e a percepção de lentidão seria brutal. Com SSE, a percepção é de fluidez — o Synthesizer Agent escreve
                "na frente do usuário" enquanto os outros agentes ainda trabalham nos bastidores.
              </div>
            </div>
          </div>
        )}
      </div>

      <style>{`
        * { box-sizing: border-box; }
        button:hover { opacity: 0.85; }
        ::-webkit-scrollbar { width: 5px; height: 5px; }
        ::-webkit-scrollbar-track { background: ${BG}; }
        ::-webkit-scrollbar-thumb { background: ${BORDER}; border-radius: 3px; }
      `}</style>
    </div>
  );
}
