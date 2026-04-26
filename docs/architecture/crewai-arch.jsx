import { useState } from "react";

const ACCENT = "#A8C5E8";
const BG = "#0A0C12";
const SURFACE = "#10141F";
const BORDER = "#1C2235";

const agents = [
  {
    id: "orchestrator",
    role: "🧠 Orchestrator Agent",
    badge: "MANAGER",
    badgeColor: "#E8946A",
    goal: "Recebe a pergunta do usuário, identifica a intenção, roteia para o Crew correto e consolida a resposta final.",
    backstory: "Agente gerente no modelo hierárquico do CrewAI. Único agente que conversa diretamente com o usuário e tem visibilidade de todo o fluxo.",
    tools: ["RouterTool", "MemoryReadTool", "ProfileDetectorTool"],
    llm: "claude-sonnet-4-5 / GPT-4o",
    color: "#E8946A",
    crew: "core",
  },
  {
    id: "profiler",
    role: "👤 Profile & Intent Agent",
    badge: "SPECIALIST",
    badgeColor: "#6C9BC7",
    goal: "Classifica o perfil do usuário (pesquisador, gestor, estudante) e decompõe a pergunta em entidades, métricas, recorte temporal e tipo de comparação.",
    backstory: "Especialista em NLU educacional. Conhece a taxonomia de indicadores do INEP, OECD e UNESCO e sabe mapear linguagem natural para queries estruturadas.",
    tools: ["IntentClassifierTool", "EntityExtractorTool", "ProfileAdapterTool"],
    llm: "claude-haiku-4-5 (rápido, baixo custo)",
    color: "#6C9BC7",
    crew: "core",
  },
  {
    id: "retriever",
    role: "🔍 Data Retrieval Agent",
    badge: "SPECIALIST",
    badgeColor: "#7CB99A",
    goal: "Traduz a intenção em SQL e executa consultas na camada Gold do Data Lakehouse via API FastAPI + DuckDB.",
    backstory: "Engenheiro de dados com conhecimento profundo do schema Gold Layer. Sabe quais tabelas contêm PISA, IDEB, UIS, Eurostat e como cruzá-las corretamente.",
    tools: ["DuckDBQueryTool", "FastAPIClientTool", "SchemaLookupTool", "QueryValidatorTool"],
    llm: "claude-sonnet-4-5",
    color: "#7CB99A",
    crew: "analysis",
  },
  {
    id: "statistician",
    role: "📐 Statistical Analyst Agent",
    badge: "SPECIALIST",
    badgeColor: "#B08FD4",
    goal: "Valida a significância estatística dos resultados, aplica metodologia correta de plausible values (PISA/TIMSS) e contextualiza os números.",
    backstory: "Estatístico com expertise em avaliações de larga escala. Sabe que resultados PISA sem BRR weights são metodologicamente inválidos para publicação.",
    tools: ["PValueTool", "ConfidenceIntervalTool", "PlausibleValuesTool", "StatContextTool"],
    llm: "claude-sonnet-4-5",
    color: "#B08FD4",
    crew: "analysis",
  },
  {
    id: "comparativist",
    role: "🌍 Comparative Education Agent",
    badge: "SPECIALIST",
    badgeColor: "#D4A04A",
    goal: "Especialista em comparações BR × Internacional. Contextualiza diferenças estruturais, históricas e socioeconômicas que explicam os dados.",
    backstory: "Pesquisador em educação comparada com conhecimento de PISA, ERCE, TIMSS, PIRLS e TALIS. Sabe as limitações de cada avaliação e os ciclos em que o Brasil participou.",
    tools: ["ComparativeLookupTool", "ContextEnricherTool", "CausalityFlagTool"],
    llm: "claude-sonnet-4-5",
    color: "#D4A04A",
    crew: "analysis",
  },
  {
    id: "citation",
    role: "📚 Citation & Evidence Agent",
    badge: "SPECIALIST",
    badgeColor: "#E87D7D",
    goal: "Recupera referências acadêmicas relevantes via RAG sobre a base de literatura e valida afirmações contra evidências publicadas.",
    backstory: "Bibliotecário científico com acesso à base RAG (ChromaDB) populada com artigos do SciELO, CAPES, ERIC, RePEc e relatórios OCDE/UNESCO.",
    tools: ["RAGSearchTool", "CitationFormatterTool", "DOIResolverTool", "EvidenceRankerTool"],
    llm: "claude-haiku-4-5",
    color: "#E87D7D",
    crew: "analysis",
  },
  {
    id: "visualizer",
    role: "📊 Visualization Agent",
    badge: "SPECIALIST",
    badgeColor: "#88C5A8",
    goal: "Gera gráficos, tabelas comparativas e infográficos baseados nos dados retornados, em formato adequado ao perfil do usuário.",
    backstory: "Designer de dados educacionais. Escolhe automaticamente o tipo de chart correto (ranking, série temporal, scatter PISA, mapa de calor) conforme o tipo de dado.",
    tools: ["PlotlyGeneratorTool", "TableFormatterTool", "ChartSelectorTool", "Base64EncoderTool"],
    llm: "claude-haiku-4-5",
    color: "#88C5A8",
    crew: "synthesis",
  },
  {
    id: "synthesizer",
    role: "✍️ Response Synthesizer Agent",
    badge: "SPECIALIST",
    badgeColor: "#C8A0D8",
    goal: "Combina dados, análise estatística, contexto comparativo, referências e visualizações em uma resposta coesa, adaptada ao perfil detectado.",
    backstory: "Comunicador científico com capacidade de traduzir análises complexas para pesquisadores, gestores e estudantes — sem perder precisão.",
    tools: ["ProfileAdapterTool", "MarkdownFormatterTool", "ToneAdjusterTool", "MemoryWriteTool"],
    llm: "claude-sonnet-4-5",
    color: "#C8A0D8",
    crew: "synthesis",
  },
];

const crews = [
  {
    id: "core",
    label: "Core Crew",
    color: "#E8946A",
    desc: "Sempre ativo. Gerencia o fluxo completo e identifica perfil/intenção.",
    agents: ["orchestrator", "profiler"],
  },
  {
    id: "analysis",
    label: "Analysis Crew",
    color: "#7CB99A",
    desc: "Ativado para perguntas que requerem dados reais do Lakehouse.",
    agents: ["retriever", "statistician", "comparativist", "citation"],
  },
  {
    id: "synthesis",
    label: "Synthesis Crew",
    color: "#C8A0D8",
    desc: "Sempre ativo ao final. Gera visualizações e a resposta final formatada.",
    agents: ["visualizer", "synthesizer"],
  },
];

const flows = [
  {
    id: "simple",
    label: "Fluxo Simples",
    color: "#6C9BC7",
    icon: "⚡",
    desc: "Pergunta conceitual ou contextual sem necessidade de dados do Lakehouse.",
    path: ["Orchestrator", "Profiler", "Comparativist (RAG)", "Synthesizer"],
    example: '"O que é o PISA e como o Brasil se posiciona historicamente?"',
    latency: "~5–10s",
  },
  {
    id: "data",
    label: "Fluxo com Dados",
    color: "#7CB99A",
    icon: "🔢",
    desc: "Pergunta que exige métricas reais, séries históricas ou comparações numéricas.",
    path: ["Orchestrator", "Profiler", "Retriever → DuckDB", "Statistician", "Comparativist", "Visualizer", "Synthesizer"],
    example: '"Compare a taxa de analfabetismo do Brasil com países da OCDE entre 2000 e 2022."',
    latency: "~20–40s",
  },
  {
    id: "deep",
    label: "Fluxo Deep Research",
    color: "#B08FD4",
    icon: "🔬",
    desc: "Análise complexa com múltiplas fontes, evidências académicas e visualizações completas.",
    path: ["Orchestrator", "Profiler", "Retriever (múltiplas queries)", "Statistician", "Comparativist", "Citation (RAG)", "Visualizer", "Synthesizer"],
    example: '"Quais fatores socioeconômicos explicam a diferença de desempenho no PISA entre Brasil e Finlândia?"',
    latency: "~60–120s",
  },
];

const tools = [
  { name: "DuckDBQueryTool", desc: "Executa SQL na Gold Layer via FastAPI local", category: "Data" },
  { name: "FastAPIClientTool", desc: "Cliente HTTP para a API intermediária do Lakehouse", category: "Data" },
  { name: "SchemaLookupTool", desc: "Consulta o catálogo OpenMetadata para descobrir tabelas", category: "Data" },
  { name: "RAGSearchTool", desc: "Busca semântica sobre literatura científica (ChromaDB)", category: "Knowledge" },
  { name: "CitationFormatterTool", desc: "Formata referências em ABNT/APA/Vancouver", category: "Knowledge" },
  { name: "PlausibleValuesTool", desc: "Aplica metodologia BRR/Jackknife para PISA/TIMSS", category: "Stats" },
  { name: "ConfidenceIntervalTool", desc: "Calcula ICs e significância estatística", category: "Stats" },
  { name: "PlotlyGeneratorTool", desc: "Gera gráficos interativos (HTML embed ou PNG)", category: "Visual" },
  { name: "TableFormatterTool", desc: "Formata tabelas comparativas em Markdown/HTML", category: "Visual" },
  { name: "ProfileAdapterTool", desc: "Ajusta tom, vocabulário e profundidade da resposta", category: "UX" },
  { name: "IntentClassifierTool", desc: "Classifica intenção: conceitual, numérica, comparativa, causal", category: "UX" },
  { name: "MemoryReadTool", desc: "Lê histórico da conversa (short-term memory)", category: "Memory" },
  { name: "MemoryWriteTool", desc: "Persiste contexto relevante da sessão", category: "Memory" },
];

const toolCategories = {
  Data: "#7CB99A",
  Knowledge: "#E87D7D",
  Stats: "#B08FD4",
  Visual: "#D4A04A",
  UX: "#6C9BC7",
  Memory: "#E8946A",
};

const techStack = [
  { layer: "Framework de Agentes", tech: "CrewAI 0.80+", note: "Processo hierárquico com Manager" },
  { layer: "LLM Principal", tech: "Claude Sonnet 4.5", note: "Raciocínio complexo e geração" },
  { layer: "LLM Rápido", tech: "Claude Haiku 4.5", note: "Classificação e tarefas simples" },
  { layer: "Memória Curto Prazo", tech: "ConversationBuffer", note: "Histórico da sessão atual" },
  { layer: "Memória Longo Prazo", tech: "ChromaDB + Embeddings", note: "RAG sobre literatura científica" },
  { layer: "Acesso ao Lakehouse", tech: "FastAPI + DuckDB", note: "API intermediária local" },
  { layer: "Interface do Usuário", tech: "Chainlit ou Streamlit", note: "Chat UI com suporte a charts" },
  { layer: "Orquestração", tech: "Prefect 3", note: "Já presente na arquitetura do Lakehouse" },
  { layer: "Logging & Trace", tech: "LangSmith / Langfuse", note: "Observabilidade dos agentes" },
];

export default function CrewAIArch() {
  const [activeAgent, setActiveAgent] = useState(null);
  const [activeFlow, setActiveFlow] = useState("data");
  const [activeTab, setActiveTab] = useState("agents");

  const agent = agents.find(a => a.id === activeAgent);
  const flow = flows.find(f => f.id === activeFlow);

  return (
    <div style={{ fontFamily: "'Georgia', serif", background: BG, minHeight: "100vh", color: "#E0DDD8" }}>

      {/* Header */}
      <div style={{
        background: "linear-gradient(135deg, #12182A 0%, #0A0C12 100%)",
        borderBottom: `1px solid ${BORDER}`,
        padding: "2.5rem 2.5rem 1.8rem",
        position: "relative", overflow: "hidden",
      }}>
        <div style={{
          position: "absolute", top: 0, left: 0, right: 0, bottom: 0,
          background: "radial-gradient(ellipse at 80% 50%, rgba(108,155,199,0.06) 0%, transparent 60%)",
          pointerEvents: "none",
        }} />
        <div style={{ fontSize: "0.65rem", letterSpacing: "0.25em", color: "#6C9BC7", marginBottom: "0.5rem", textTransform: "uppercase" }}>
          Sistema Multi-Agente · CrewAI · Educação Comparada BR × Internacional
        </div>
        <h1 style={{ fontSize: "clamp(1.5rem, 2.5vw, 2.2rem)", margin: 0, fontWeight: 400, color: "#F0EDE6", letterSpacing: "-0.02em" }}>
          Arquitetura de Agentes Inteligentes
        </h1>
        <p style={{ margin: "0.6rem 0 0", color: "#6A6660", fontSize: "0.88rem", maxWidth: "580px", lineHeight: 1.6 }}>
          Processo Hierárquico · 8 Agentes Especializados · 3 Crews · RAG + DuckDB + Visualização Adaptativa
        </p>
      </div>

      {/* Tabs */}
      <div style={{ background: SURFACE, borderBottom: `1px solid ${BORDER}`, padding: "0 2.5rem", display: "flex", gap: "0" }}>
        {[
          { id: "agents", label: "Agentes & Crews" },
          { id: "flows", label: "Fluxos de Execução" },
          { id: "tools", label: "Ferramentas (Tools)" },
          { id: "stack", label: "Stack Tecnológico" },
        ].map(tab => (
          <button key={tab.id} onClick={() => setActiveTab(tab.id)} style={{
            background: "none", border: "none", cursor: "pointer",
            padding: "1rem 1.2rem",
            color: activeTab === tab.id ? ACCENT : "#5A5860",
            borderBottom: `2px solid ${activeTab === tab.id ? ACCENT : "transparent"}`,
            fontSize: "0.82rem", letterSpacing: "0.05em",
            transition: "color 0.15s",
          }}>{tab.label}</button>
        ))}
      </div>

      <div style={{ padding: "2rem 2.5rem", maxWidth: "1200px", margin: "0 auto" }}>

        {/* TAB: Agentes & Crews */}
        {activeTab === "agents" && (
          <div>
            {/* Crews overview */}
            <div style={{ marginBottom: "2rem" }}>
              <div style={{ fontSize: "0.65rem", color: "#5A5860", letterSpacing: "0.2em", textTransform: "uppercase", marginBottom: "1rem" }}>
                Estrutura de Crews — Processo Hierárquico
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "1rem" }}>
                {crews.map(crew => (
                  <div key={crew.id} style={{
                    padding: "1.25rem",
                    background: SURFACE,
                    border: `1px solid ${crew.color}40`,
                    borderTop: `3px solid ${crew.color}`,
                    borderRadius: "8px",
                  }}>
                    <div style={{ fontSize: "0.65rem", color: crew.color, letterSpacing: "0.2em", textTransform: "uppercase", marginBottom: "0.3rem" }}>{crew.label}</div>
                    <div style={{ fontSize: "0.78rem", color: "#7A7670", lineHeight: 1.6, marginBottom: "0.8rem" }}>{crew.desc}</div>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "0.3rem" }}>
                      {crew.agents.map(aid => {
                        const ag = agents.find(a => a.id === aid);
                        return (
                          <span key={aid} style={{
                            padding: "0.2rem 0.5rem", borderRadius: "4px",
                            background: ag.color + "18", color: ag.color,
                            fontSize: "0.65rem", fontFamily: "monospace",
                          }}>{ag.role.split(" ").slice(1).join(" ")}</span>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Agent grid */}
            <div style={{ fontSize: "0.65rem", color: "#5A5860", letterSpacing: "0.2em", textTransform: "uppercase", marginBottom: "1rem" }}>
              Clique em um agente para ver os detalhes
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))", gap: "0.8rem", marginBottom: "1.5rem" }}>
              {agents.map(ag => (
                <div key={ag.id}
                  onClick={() => setActiveAgent(activeAgent === ag.id ? null : ag.id)}
                  style={{
                    padding: "1.1rem 1.25rem",
                    background: activeAgent === ag.id ? `${ag.color}15` : SURFACE,
                    border: `1px solid ${activeAgent === ag.id ? ag.color + "70" : BORDER}`,
                    borderLeft: `3px solid ${ag.color}`,
                    borderRadius: "8px",
                    cursor: "pointer",
                    transition: "all 0.15s",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "0.4rem" }}>
                    <div style={{ fontSize: "0.88rem", color: ag.color, fontWeight: 600 }}>{ag.role}</div>
                    <span style={{
                      fontSize: "0.55rem", padding: "0.15rem 0.4rem", borderRadius: "3px",
                      background: ag.badgeColor + "25", color: ag.badgeColor, letterSpacing: "0.1em",
                    }}>{ag.badge}</span>
                  </div>
                  <div style={{ fontSize: "0.75rem", color: "#6A6660", lineHeight: 1.55 }}>{ag.goal.substring(0, 100)}…</div>
                </div>
              ))}
            </div>

            {/* Agent detail panel */}
            {agent && (
              <div style={{
                background: `${agent.color}0C`,
                border: `1px solid ${agent.color}50`,
                borderRadius: "12px",
                padding: "1.75rem 2rem",
                animation: "slideIn 0.2s ease",
              }}>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "2rem" }}>
                  <div>
                    <div style={{ fontSize: "1.1rem", color: agent.color, fontWeight: 600, marginBottom: "0.8rem" }}>{agent.role}</div>
                    <div style={{ fontSize: "0.7rem", color: "#5A5860", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: "0.3rem" }}>Goal</div>
                    <div style={{ fontSize: "0.82rem", color: "#A0A098", lineHeight: 1.65, marginBottom: "1rem" }}>{agent.goal}</div>
                    <div style={{ fontSize: "0.7rem", color: "#5A5860", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: "0.3rem" }}>Backstory</div>
                    <div style={{ fontSize: "0.82rem", color: "#7A7670", lineHeight: 1.65 }}>{agent.backstory}</div>
                  </div>
                  <div>
                    <div style={{ fontSize: "0.7rem", color: "#5A5860", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: "0.6rem" }}>Tools</div>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "0.4rem", marginBottom: "1.2rem" }}>
                      {agent.tools.map(t => (
                        <span key={t} style={{
                          padding: "0.25rem 0.6rem", borderRadius: "4px",
                          background: "#1A2030", color: "#8A9AB8",
                          fontSize: "0.7rem", fontFamily: "monospace",
                        }}>{t}</span>
                      ))}
                    </div>
                    <div style={{ fontSize: "0.7rem", color: "#5A5860", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: "0.3rem" }}>LLM</div>
                    <div style={{ fontSize: "0.82rem", color: agent.color, fontFamily: "monospace" }}>{agent.llm}</div>
                    <div style={{ marginTop: "1.2rem", padding: "0.75rem", background: "#0A0C12", borderRadius: "6px" }}>
                      <div style={{ fontSize: "0.65rem", color: "#5A5860", marginBottom: "0.3rem", textTransform: "uppercase", letterSpacing: "0.1em" }}>Crew</div>
                      <div style={{ fontSize: "0.8rem", color: crews.find(c => c.id === agent.crew)?.color }}>
                        {crews.find(c => c.id === agent.crew)?.label}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* TAB: Fluxos */}
        {activeTab === "flows" && (
          <div>
            <div style={{ display: "flex", gap: "0.75rem", marginBottom: "1.75rem" }}>
              {flows.map(f => (
                <button key={f.id} onClick={() => setActiveFlow(f.id)} style={{
                  padding: "0.6rem 1.2rem",
                  background: activeFlow === f.id ? f.color + "20" : SURFACE,
                  border: `1px solid ${activeFlow === f.id ? f.color + "80" : BORDER}`,
                  borderRadius: "6px", cursor: "pointer", color: activeFlow === f.id ? f.color : "#6A6660",
                  fontSize: "0.82rem", fontFamily: "inherit",
                  transition: "all 0.15s",
                }}>{f.icon} {f.label}</button>
              ))}
            </div>

            {flow && (
              <div>
                <div style={{
                  padding: "1.5rem", background: SURFACE,
                  border: `1px solid ${flow.color}40`,
                  borderRadius: "10px", marginBottom: "1.5rem",
                }}>
                  <div style={{ fontSize: "0.82rem", color: "#8A8680", lineHeight: 1.6, marginBottom: "1rem" }}>{flow.desc}</div>
                  <div style={{ fontSize: "0.75rem", color: "#5A5860", marginBottom: "0.4rem", textTransform: "uppercase", letterSpacing: "0.1em" }}>Exemplo de pergunta</div>
                  <div style={{
                    fontFamily: "monospace", fontSize: "0.82rem",
                    color: flow.color, background: "#0A0C12",
                    padding: "0.75rem 1rem", borderRadius: "6px",
                    borderLeft: `3px solid ${flow.color}`,
                  }}>{flow.example}</div>
                  <div style={{ marginTop: "0.8rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
                    <span style={{ fontSize: "0.65rem", color: "#5A5860", textTransform: "uppercase", letterSpacing: "0.1em" }}>Latência esperada:</span>
                    <span style={{ fontSize: "0.8rem", color: flow.color, fontFamily: "monospace" }}>{flow.latency}</span>
                  </div>
                </div>

                {/* Flow path visualization */}
                <div style={{ fontSize: "0.65rem", color: "#5A5860", textTransform: "uppercase", letterSpacing: "0.2em", marginBottom: "1rem" }}>
                  Sequência de execução
                </div>
                <div style={{ display: "flex", flexWrap: "wrap", alignItems: "center", gap: "0.3rem", marginBottom: "2rem" }}>
                  {flow.path.map((step, i) => (
                    <div key={i} style={{ display: "flex", alignItems: "center", gap: "0.3rem" }}>
                      <div style={{
                        padding: "0.5rem 0.9rem",
                        background: flow.color + "18",
                        border: `1px solid ${flow.color}50`,
                        borderRadius: "6px",
                        fontSize: "0.75rem", color: flow.color,
                        fontFamily: "monospace", whiteSpace: "nowrap",
                      }}>{step}</div>
                      {i < flow.path.length - 1 && (
                        <span style={{ color: "#2A2E3E", fontSize: "1rem" }}>→</span>
                      )}
                    </div>
                  ))}
                </div>

                {/* Decision logic */}
                <div style={{
                  background: SURFACE, border: `1px solid ${BORDER}`,
                  borderRadius: "10px", padding: "1.5rem",
                }}>
                  <div style={{ fontSize: "0.65rem", color: "#5A5860", textTransform: "uppercase", letterSpacing: "0.2em", marginBottom: "1.2rem" }}>
                    Lógica de roteamento do Orchestrator
                  </div>
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "1rem" }}>
                    {[
                      { q: "Pergunta conceitual?", then: "Fluxo Simples", note: "sem SQL, só RAG + contexto" },
                      { q: "Requer dados numéricos?", then: "Fluxo com Dados", note: "aciona Retriever + DuckDB" },
                      { q: "Análise causal/multifator?", then: "Deep Research", note: "todos os agentes + literatura" },
                    ].map((row, i) => (
                      <div key={i} style={{ padding: "1rem", background: "#0A0C12", borderRadius: "8px" }}>
                        <div style={{ fontSize: "0.7rem", color: "#5A9A9A", fontFamily: "monospace", marginBottom: "0.4rem" }}>if {row.q}</div>
                        <div style={{ fontSize: "0.8rem", color: ACCENT, fontWeight: 600, marginBottom: "0.2rem" }}>→ {row.then}</div>
                        <div style={{ fontSize: "0.7rem", color: "#5A5860" }}>{row.note}</div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* TAB: Tools */}
        {activeTab === "tools" && (
          <div>
            <div style={{ marginBottom: "1.25rem", display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
              {Object.entries(toolCategories).map(([cat, color]) => (
                <span key={cat} style={{
                  padding: "0.25rem 0.7rem", borderRadius: "100px",
                  background: color + "20", color,
                  fontSize: "0.7rem", letterSpacing: "0.05em",
                }}>● {cat}</span>
              ))}
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: "0.75rem" }}>
              {tools.map(tool => {
                const color = toolCategories[tool.category];
                return (
                  <div key={tool.name} style={{
                    padding: "1rem 1.2rem",
                    background: SURFACE,
                    border: `1px solid ${BORDER}`,
                    borderLeft: `3px solid ${color}`,
                    borderRadius: "8px",
                  }}>
                    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.35rem" }}>
                      <span style={{ fontFamily: "monospace", fontSize: "0.78rem", color }}>{tool.name}</span>
                      <span style={{
                        fontSize: "0.6rem", padding: "0.1rem 0.4rem",
                        background: color + "20", color,
                        borderRadius: "3px", letterSpacing: "0.05em",
                      }}>{tool.category}</span>
                    </div>
                    <div style={{ fontSize: "0.76rem", color: "#6A6660", lineHeight: 1.55 }}>{tool.desc}</div>
                  </div>
                );
              })}
            </div>

            {/* Tool implementation note */}
            <div style={{
              marginTop: "1.5rem", padding: "1.25rem 1.5rem",
              background: "linear-gradient(135deg, #101A10 0%, #0A0C12 100%)",
              border: "1px solid #1E3020",
              borderRadius: "10px",
            }}>
              <div style={{ fontSize: "0.7rem", color: "#7CB99A", textTransform: "uppercase", letterSpacing: "0.15em", marginBottom: "0.6rem" }}>
                Como implementar as tools no CrewAI
              </div>
              <pre style={{
                fontFamily: "monospace", fontSize: "0.75rem",
                color: "#8AA890", lineHeight: 1.7, margin: 0,
                overflowX: "auto",
              }}>{`from crewai.tools import BaseTool
import duckdb, httpx

class DuckDBQueryTool(BaseTool):
    name: str = "DuckDBQueryTool"
    description: str = (
        "Executa SQL na Gold Layer do Lakehouse educacional. "
        "Input: query SQL válida. Output: DataFrame em JSON."
    )
    
    def _run(self, query: str) -> str:
        conn = duckdb.connect("/data/gold/education.duckdb")
        result = conn.execute(query).df()
        return result.to_json(orient="records", force_ascii=False)`}</pre>
            </div>
          </div>
        )}

        {/* TAB: Stack */}
        {activeTab === "stack" && (
          <div>
            <div style={{ display: "grid", gap: "0.65rem", marginBottom: "2rem" }}>
              {techStack.map(item => (
                <div key={item.layer} style={{
                  display: "grid", gridTemplateColumns: "220px 200px 1fr",
                  alignItems: "center", gap: "1rem",
                  padding: "0.9rem 1.25rem",
                  background: SURFACE, border: `1px solid ${BORDER}`,
                  borderRadius: "8px",
                }}>
                  <div style={{ fontSize: "0.75rem", color: "#6A6660" }}>{item.layer}</div>
                  <div style={{ fontFamily: "monospace", fontSize: "0.82rem", color: ACCENT }}>{item.tech}</div>
                  <div style={{ fontSize: "0.75rem", color: "#4A4848" }}>{item.note}</div>
                </div>
              ))}
            </div>

            {/* Integration diagram */}
            <div style={{
              background: SURFACE, border: `1px solid ${BORDER}`,
              borderRadius: "12px", padding: "1.75rem",
            }}>
              <div style={{ fontSize: "0.65rem", color: "#5A5860", textTransform: "uppercase", letterSpacing: "0.2em", marginBottom: "1.5rem" }}>
                Integração: Chatbot ↔ Data Lakehouse
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: "0.6rem" }}>
                {[
                  { from: "Chainlit UI", arrow: "pergunta do usuário", to: "CrewAI Orchestrator", color: "#6C9BC7" },
                  { from: "CrewAI Retriever", arrow: "GET /query?sql=...", to: "FastAPI (porta 8000)", color: "#7CB99A" },
                  { from: "FastAPI", arrow: "SQL execution", to: "DuckDB → Gold Layer", color: "#7CB99A" },
                  { from: "Citation Agent", arrow: "semantic search", to: "ChromaDB (literatura RAG)", color: "#E87D7D" },
                  { from: "Visualizer Agent", arrow: "fig.to_json()", to: "Plotly HTML embed", color: "#D4A04A" },
                  { from: "Synthesizer Agent", arrow: "resposta formatada", to: "Chainlit UI (Markdown + Chart)", color: "#C8A0D8" },
                ].map((row, i) => (
                  <div key={i} style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
                    <span style={{ fontFamily: "monospace", fontSize: "0.75rem", color: row.color, minWidth: "180px", textAlign: "right" }}>{row.from}</span>
                    <span style={{ color: "#2A2E3E", fontSize: "0.8rem" }}>──</span>
                    <span style={{ fontSize: "0.68rem", color: "#4A4858", fontStyle: "italic", minWidth: "160px" }}>{row.arrow}</span>
                    <span style={{ color: "#2A2E3E", fontSize: "0.8rem" }}>──▶</span>
                    <span style={{ fontFamily: "monospace", fontSize: "0.75rem", color: "#8A8880" }}>{row.to}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Key architectural decision */}
            <div style={{
              marginTop: "1.5rem",
              display: "grid", gridTemplateColumns: "1fr 1fr",
              gap: "1rem",
            }}>
              {[
                {
                  title: "Por que FastAPI entre os agentes e o DuckDB?",
                  color: "#7CB99A",
                  body: "Isola os agentes do schema do banco. Permite validação de SQL, rate limiting, autenticação e logging centralizado — sem expor o DuckDB diretamente aos agentes.",
                },
                {
                  title: "Por que ChromaDB para o RAG de literatura?",
                  color: "#E87D7D",
                  body: "Leve, embarcado, sem servidor adicional. Indexa abstracts + metadados de artigos SciELO/ERIC/CAPES. Busca semântica com sentence-transformers (multilingual).",
                },
                {
                  title: "Por que processo Hierárquico no CrewAI?",
                  color: "#E8946A",
                  body: "O Orchestrator decide quais agentes acionar conforme a complexidade da pergunta. Evita ativar todos os agentes para perguntas simples — economiza tokens e latência.",
                },
                {
                  title: "Por que Chainlit e não Gradio/Streamlit?",
                  color: "#C8A0D8",
                  body: "Chainlit é projetado especificamente para chat com LLMs. Suporta streaming, steps de reasoning visíveis, upload de arquivos e renderização de Markdown + Plotly nativamente.",
                },
              ].map(card => (
                <div key={card.title} style={{
                  padding: "1.25rem", background: "#0A0C12",
                  border: `1px solid ${card.color}30`,
                  borderTop: `2px solid ${card.color}`,
                  borderRadius: "8px",
                }}>
                  <div style={{ fontSize: "0.8rem", color: card.color, fontWeight: 600, marginBottom: "0.5rem" }}>{card.title}</div>
                  <div style={{ fontSize: "0.76rem", color: "#6A6660", lineHeight: 1.65 }}>{card.body}</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      <style>{`
        @keyframes slideIn { from { opacity: 0; transform: translateY(-6px); } to { opacity: 1; transform: translateY(0); } }
        * { box-sizing: border-box; }
        button:hover { opacity: 0.9; }
        ::-webkit-scrollbar { width: 5px; height: 5px; }
        ::-webkit-scrollbar-track { background: #0A0C12; }
        ::-webkit-scrollbar-thumb { background: #1C2235; border-radius: 3px; }
      `}</style>
    </div>
  );
}
