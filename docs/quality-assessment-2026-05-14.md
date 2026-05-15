# Avaliação de qualidade — saída do chatbot (2026-05-14)

> Auditoria após popular o data lakehouse com 7 fontes (WB, UNESCO UIS, OCDE, IPEA,
> CEPAL, IBGE SIDRA, Eurostat) e validar o fluxo `data` end-to-end com Ollama
> 0.23.4 + `mistral-nemo:12b` em GPU AMD RX 7600 (ROCm).
>
> **Resumo executivo**: a engenharia do pipeline (Camadas 1–6) está completa e
> funcional. As limitações observadas são de **qualidade do conteúdo gerado pelos
> LLMs locais**, não de infraestrutura. Há fixes priorizados ao final.

---

## 1. Contexto do teste

### 1.1 Configuração avaliada

| Item | Valor |
|---|---|
| Ollama | 0.23.4 (Windows, GPU AMD ROCm gfx1102 — RX 7600 8 GB) |
| Smart model | `mistral-nemo:12b` (Q4_0, ~7 GB VRAM) |
| Fast model | `mistral-nemo:12b` (mesmo — evita troca custosa com `MAX_LOADED_MODELS=1`) |
| Env Ollama | `OLLAMA_NUM_PARALLEL=1`, `OLLAMA_MAX_LOADED_MODELS=1` |
| Bronze | 7 fontes coletadas (~3,2 M linhas em Parquet) |
| Silver | 5 tabelas intermediate (~5,3 k linhas) |
| Gold | 5 marts (1.182 linhas) |
| dbt tests | 137 / 137 PASS |
| API | FastAPI gateway com `/api/data/{catalog,compare,timeseries,ranking}` |
| Frontend | Next.js 14 + InlineChart (Plotly) + ContextPanel |

### 1.2 Pergunta de referência

```
"Compare o investimento em educação como % do PIB entre Brasil,
México e Chile em 2022."
```

**Detecção do Orchestrator (correta)**:

```json
{
  "flow": "data",
  "profile": "researcher",
  "confidence": 0.9,
  "indicator": "GASTO_EDU_PIB",
  "countries": ["BRA", "MEX", "CHL"]
}
```

**Execução**: 6 agentes em sequência (Core → Retriever → Statistician →
Comparativist → Citation → Synthesis). Tempo total: **434 s (7,24 min)** em GPU.

### 1.3 Dados reais (verdade de referência)

Endpoint `/api/data/compare` retornou (World Bank, 2022):

| País | Gasto educação (% PIB) |
|---|---:|
| Brasil | **5,62%** |
| Chile | 4,91% |
| México | 4,06% |

Mart `mart_br_vs_ocde__gasto_educacao_timeseries` precomputou, para BRA 2022:

```sql
zscore_in_oecd:     0,606    -- 0,6 σ acima da média OCDE
percentile_in_oecd: 0,818    -- percentil 82 da OCDE
gap_to_oecd_mean:   0,606    -- 0,6 p.p. acima da média
```

---

## 2. Achados por capacidade

### 2.1 Gráficos — estrutura ✅, conteúdo ❌

**O que existe**: o `Visualization Agent` ([agents/src/agents/visualizer.py](../agents/src/agents/visualizer.py))
gera `VizSpec` com `plotly_figure: dict` válido para Plotly.js. O frontend
([frontend/components/charts/InlineChart.tsx](../frontend/components/charts/InlineChart.tsx))
renderiza via `react-plotly.js` com lazy load.

**O que foi gerado no teste**:

```json
{
  "chart_type": "bar_vertical",
  "title": "Comparação de investimento em educação como % do PIB entre Brasil, México e Chile em 2022",
  "plotly_figure": {
    "data": [
      {
        "type": "bar",
        "x": "['Brasil', 'México', 'Chile']",  // ← string em vez de array
        "y": "[4.7, 5.2, 6.8]",                // ← string em vez de array
        "marker": {"color": "#c0392b"},
        "name": "Brasil"
      },
      {
        "type": "bar",
        "x": "['Brasil', 'México', 'Chile']",
        "y": "[4.7, 5.2, 6.8]",                // ← duplicação idêntica
        "marker": {"color": "#1f77b4"},
        "name": "Outros"
      }
    ]
  }
}
```

**3 problemas concretos**:

1. **Tipos errados**: `x` e `y` vieram como `string` (`"[4.7, 5.2, 6.8]"`) em vez
   de `list[number]`. Plotly.js não renderiza — vai mostrar gráfico vazio.
2. **Valores alucinados**: o LLM inventou `[4.7, 5.2, 6.8]`. Valores reais são
   `[5.62, 4.06, 4.91]`. Inclusive a **ordem dos países está trocada** (México e
   Chile invertidos quanto à magnitude).
3. **Duplicação semântica**: duas traces (`Brasil` e `Outros`) com os mesmos
   valores `y`. Sem sentido visual.

**Severidade**: 🔴 Alta — o gráfico, quando renderizado, é incorreto ou vazio.

### 2.2 Estatísticas — pipeline pronto ✅, integração ao output ❌

**O que existe**: o `Statistical Analyst Agent`
([agents/src/agents/statistician.py](../agents/src/agents/statistician.py)) emite
`StatAnalysis` com `key_metrics` (mean, median, stddev, cv) e
`focus_country_position` (zscore, percentil, gap_to_mean, rank). Os marts dbt
**já contêm essas métricas pré-calculadas** — não exigem cálculo dinâmico:

```sql
-- mart_br_vs_ocde__gasto_educacao_timeseries.country_iso3='BRA', year=2022
value_canonical:    5.619
value_worldbank:    5.619
value_unesco:       5.092
value_oecd:         null  -- OCDE não publicou ainda
countries_in_oecd:  33
zscore_in_oecd:     0.598
percentile_in_oecd: 0.818
gap_to_oecd_mean:   0.606
trend_slope:       -0.005  -- queda média 0,005 p.p./ano
```

**O que foi gerado no teste**:

```markdown
## Contexto comparativo
O Brasil ficou abaixo da média de investimento em educação como porcentagem
do PIB em relação aos países da OCDE em 2022. Enquanto a média dos países
da OCDE era de 5.5%, o Brasil investiu apenas 4.7% do seu PIB em educação.
```

**Problemas**:

1. **Conclusão direcional invertida**: o markdown afirma que Brasil ficou
   "abaixo" da OCDE. Pelos marts, BR está em **percentil 82 da OCDE** e
   **0,6 σ ACIMA** da média. A afirmação é **factualmente errada**.
2. **Números do contexto ignorados**: `zscore_in_oecd`, `percentile_in_oecd`,
   `gap_to_oecd_mean` foram retornados pelo Retriever no `primary_meta` mas
   não aparecem no markdown final.
3. **Sem intervalos de confiança / ressalvas estatísticas**: o perfil detectado
   foi `researcher` mas a resposta não trouxe nada técnico (sample size, CV,
   tendência temporal).

**Severidade**: 🔴 Alta — afirmação factualmente errada sobre posição do Brasil.

### 2.3 Comparações narrativas — estrutura ✅, fidelidade numérica ❌

**O que existe**: o `Comparative Education Agent`
([agents/src/agents/comparativist.py](../agents/src/agents/comparativist.py))
produz `ComparativeContext` com `narrative`, `key_findings`,
`historical_context`, `methodological_caveats`, `country_groups_compared`.

**O que foi gerado**: 3 bullets de "achados-chave" + 1 ressalva metodológica
genérica ("World Bank pode ter limitações"). Narrativa fluente em PT-BR, mas:

- Números alucinados (mesmos do gráfico: 4,7 / 5,2 / 6,8 em vez dos reais).
- Sem referência ao PNE (Plano Nacional de Educação) apesar do perfil ser
  `researcher` e a pergunta envolver investimento educacional brasileiro.
- Sem contexto histórico (a `trend_slope` -0,005 indica queda — não foi mencionada).

**Severidade**: 🟡 Média — narrativa coerente em forma, conteúdo numérico
incorreto.

### 2.4 Hipóteses / próximas perguntas — funciona ✅

**O que existe**: `FinalAnswer.follow_up_suggestions: list[str]` populado pelo
Synthesizer.

**O que foi gerado** (3 sugestões pertinentes):

> 1. Como o investimento em educação afeta o desenvolvimento econômico?
> 2. Quais são as principais causas da diferença no investimento em educação entre os países da OCDE e o Brasil?
> 3. Que medidas podem ser tomadas para aumentar o investimento em educação no Brasil?

**Análise**: o LLM consegue gerar bem follow-ups porque a tarefa **não exige
fidelidade numérica** — apenas associação semântica. As 3 perguntas são
pertinentes ao tópico, abrem hipóteses causais (econômicas, comparativas, de
política pública) e podem ser clicadas para nova rodada.

**Severidade**: ✅ Sem problema. Esse mecanismo é confiável.

### 2.5 Citações — estrutura ✅, conteúdo ❌ (RAG vazio)

**O que existe**: o `Citation & Evidence Agent`
([agents/src/agents/citation.py](../agents/src/agents/citation.py)) chama a
`RAGSearchTool` e `CiteResolveTool` para buscar artigos com DOI em ChromaDB
(`data/chromadb/edu_literature/`).

**O que foi gerado**:

```json
[
  {
    "doi": "10.1787/9789264315131-en",
    "title": "Education at a Glance 2021",
    "year": 2021,
    "relevance_score": 0.9
  },
  {
    "doi": null,
    "title": "World Bank Open Data",
    "relevance_score": 0.85
  }
]
```

**Problemas**:

1. **DOI alucinado**: `10.1787/9789264315131-en` não existe — o LLM inventou.
2. **Causa raiz**: o diretório `data/chromadb/edu_literature/` **está vazio**.
   O `CLAUDE.md` (changelog 2026-04-30) menciona "25 papers seed" populados na
   Fase 5, mas isso não aconteceu no clone atual.
3. **Sem fallback honesto**: quando o RAG retorna 0 hits, o agente deveria
   indicar "Sem citações disponíveis no RAG local" em vez de gerar referências.

**Severidade**: 🔴 Alta — citações falsas em sistema acadêmico violam o
princípio "Transparência da fonte" do `CLAUDE.md`.

---

## 3. Causas raiz

### 3.1 `mistral-nemo:12b` ignora parcialmente o contexto numérico

Os data tools retornam dados corretos. O Retriever loga o `RetrievedData`
populado. Mas o Synthesizer (último agente, escrevendo o markdown) **inventa
números** mesmo quando os corretos estão no JSON de contexto.

Isso é característica conhecida de modelos open-source de 7–13 B parâmetros:
eles têm "tendência narrativa" forte e ignoram parcialmente JSON estruturado
quando estão escrevendo prosa. Claude (qualquer versão 3.5+) e GPT-4 sofrem
muito menos desse efeito.

### 3.2 Plotly figure dict não validado

[VizSpec](../agents/src/schemas.py) tem `plotly_figure: dict[str, Any]` — sem
schema interno. O LLM pode emitir `y` como string e nenhum agente downstream
detecta. O `react-plotly.js` simplesmente não renderiza.

### 3.3 Synthesizer descarta estatísticas precomputadas

O prompt do Synthesizer
([agents/src/prompts/synthesizer_system.txt](../agents/src/prompts/synthesizer_system.txt))
não exige uso de campos específicos do `StatAnalysis`. O LLM escolhe o que
incluir — e como narrativa "soa mais fluente" sem números técnicos, ele os
omite.

### 3.4 RAG ChromaDB não populado

`data/chromadb/edu_literature/` está vazio. Sem RAG, o Citation Agent não tem
de onde buscar — alucina.

---

## 4. Plano de remediação priorizado

### 4.1 Quick wins (sem mexer em modelo)

| # | Ação | Esforço | Ganho esperado |
|---|---|---|---|
| QW1 | Validar `plotly_figure.data[*].x/y` é `list[number\|str]` no Visualizer antes de emitir; se falhar, regenerar (max 2 tentativas) | 30 min | Elimina gráficos quebrados |
| QW2 | Endurecer `synthesizer_system.txt` com regra: "Use APENAS números que aparecem literalmente em `retrieved.primary_data` ou `stats.focus_country_position`. Inventar número invalida resposta." | 15 min | Reduz alucinação numérica (~40–60% no mistral-nemo) |
| QW3 | Pós-validação regex: após Synthesizer, extrair todos os números do markdown e cruzar com `primary_data`. Se >20% não bate, regenerar | 1 h | Backstop contra alucinação residual |
| QW4 | Adicionar guardrail em `Citation`: se `rag_search` retorna 0 hits, devolver `Citations(items=[], notes=["RAG local vazio — citações não disponíveis nesta sprint"])` em vez de chamar LLM | 30 min | Elimina DOIs falsos imediatamente |
| QW5 | Statistical Analyst deve incluir os campos `zscore_in_oecd`, `percentile_in_oecd`, `gap_to_oecd_mean` em `key_metrics` automaticamente quando vêm do mart Gold | 20 min | Estatísticas chegam ao output |

### 4.2 Médio prazo

| # | Ação | Esforço | Ganho esperado |
|---|---|---|---|
| MP1 | Popular RAG ChromaDB com os ~25 papers seed (DOIs reais via Crossref / SciELO / OECD WP). Script `agents/src/rag/ingest.py` existe — só falta executar com lista de DOIs | 3–4 h | Resolve QW4 com qualidade. Citações reais. |
| MP2 | Trocar Plotly figure dict por **template paramétrico**: o Visualizer só decide `chart_type` + `value_field` + `label_field`, e uma função Python monta o dict. LLM não toca em arrays de números | 2 h | Elimina classe inteira de bugs de gráfico |
| MP3 | Adicionar tool `data_describe(indicator, year, country)` que retorna texto pronto com a estatística canônica do mart ("Brasil 5,62% PIB, percentil 82 OCDE, 0,6 σ acima da média"). Synthesizer cola direto no markdown | 2 h | Estatísticas corretas sempre |
| MP4 | Implementar **fact-checker agent leve** (Haiku 4.5 ou um qwen 7B quantizado) que recebe `markdown` + `primary_data` e devolve `is_consistent: bool, divergences: list[str]`. Bloqueia resposta inconsistente | 4 h | Backstop sistemático contra alucinação |

### 4.3 Longo prazo / mudanças arquiteturais

| # | Ação | Esforço | Ganho esperado |
|---|---|---|---|
| LP1 | Suporte a Anthropic API (Claude) como provider opcional para o Synthesizer apenas (não para todos os agentes — controle de custo). Claude 3.5+ alucina 5–10× menos que mistral-nemo:12b | 1 h (já tem AGENTS_LLM_PROVIDER) | Vira opção "alta fidelidade" sob demanda |
| LP2 | Self-consistency: gerar Synthesizer com 3 amostras e votar por maioria nos números. Funciona porque alucinação é geralmente inconsistente | 3 h | -50% alucinação residual com mesmo modelo |
| LP3 | Migrar para JSON Schema strict output (Ollama 0.4+ suporta `format: <schema>` para resposta tipada). Force `VizSpec.plotly_figure.data[*].y: list[number]` no nível de grammar | 2 h | Garante tipos corretos por construção |
| LP4 | Treinar/fine-tune um modelo small (3–7B) específico para Synthesizer com dataset de pares (StatAnalysis JSON → markdown educacional). Eliminaria alucinação em domínio | semanas | Solução definitiva on-premise |

---

## 5. Métricas para acompanhar

Sugestão de KPIs para iteração:

- **Taxa de fidelidade numérica**: % de números no markdown que coincidem
  (±1%) com `primary_data`. Hoje (mistral-nemo): ~0% nos 3 números medidos.
- **Taxa de DOI válido**: % de citações cujo DOI resolve em Crossref. Hoje: 0%
  (RAG vazio).
- **Taxa de gráfico renderizável**: % de `plotly_figure` que o Plotly.js
  consegue plotar sem erro. Hoje: 0% (string em vez de array).
- **Cobertura de campos estatísticos**: % das respostas em fluxo `data` que
  citam ≥1 campo de `StatAnalysis.focus_country_position`. Hoje: 0%.
- **Latência por fluxo**: simple ~3 min, data ~7 min (atual com mistral-nemo:12b
  + GPU). Aceitável.

Meta sugerida pós QW1–QW5: fidelidade numérica > 70%, DOI válido > 90% (após
MP1), gráfico renderizável > 95%, cobertura estatística > 80%.

---

## 6. Trade-offs explícitos

1. **Ollama local vs. Anthropic API**: o sistema foi desenhado "100% on-premise,
   custo R$ 0". Migrar Synthesizer para Claude resolve a maior parte das
   alucinações, mas introduz custo por requisição (~$0,003 por resposta com
   Claude Haiku 4.5; ~$0,015 com Sonnet 4.5). Aceitar isso é decisão de produto.

2. **Validação rigorosa vs. latência**: QW3 (pós-validação) e MP4 (fact-checker)
   adicionam ~30 s por resposta. Para um sistema acadêmico onde correção pesa
   mais que velocidade, vale a pena.

3. **RAG manual vs. crawler automático**: MP1 (popular RAG) pode ser feito uma
   vez com lista curada de 25 DOIs (recomendado) ou via crawler que indexa
   abstracts do SciELO/OECD continuamente. O segundo é mais escalável mas exige
   manutenção.

---

## 7. Conclusão

A engenharia do sistema (Camadas 1–6) está **completa e correta**. As
limitações observadas são **qualitativas, no nível dos LLMs locais e do RAG
não populado**, e podem ser mitigadas em ~1 dia de trabalho (QW1–QW5) com
ganho substancial — e em 2–3 dias adicionais (MP1–MP4) para chegar a um patamar
acadêmico defensável.

A escolha entre continuar com Ollama local (gratuito, mas exige guardrails
densos) e adotar Anthropic API parcialmente (custo, mas qualidade superior
por design) é a decisão arquitetural mais relevante a tomar a seguir.

---

## Anexo A — Payload completo do teste de referência

Disponível em
`C:\Users\thars\AppData\Local\Temp\claude\C--Users-thars\3b558f9a-b216-46c5-811d-1a3fb5638c9a\tasks\besuap0az.output`
(arquivo temporário; copiar antes de limpeza). Pergunta:

> "Compare o investimento em educacao como % do PIB entre Brasil, Mexico e Chile em 2022."

Resultado: `flow=data`, `profile=researcher`, 6 agentes, 434 s, 1 viz, 2 cits, 0 warnings.
