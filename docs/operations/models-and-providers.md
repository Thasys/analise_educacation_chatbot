# Modelos LLM e providers

O sistema é **provider-agnóstico** via [LiteLLM](https://litellm.ai) embutido
no CrewAI. A escolha vive em `.env` e afeta todos os 8 agentes.

## Variáveis de ambiente

```bash
AGENTS_LLM_PROVIDER       # anthropic | openai | gemini | groq | ollama | openrouter
AGENTS_LLM_SMART_MODEL    # modelo "smart" (Statistician, Comparativist, Synthesizer)
AGENTS_LLM_FAST_MODEL     # modelo "fast" (Orchestrator, Profiler, Retriever, Citation, Visualizer)
AGENTS_LLM_API_KEY        # chave (vazio para Ollama)
AGENTS_LLM_API_BASE       # endpoint custom (opcional)
```

`make_llm("smart"|"fast")` em [`agents/src/llm.py`](../../agents/src/llm.py)
mapeia o nome de papel para o ID do modelo.

## Configuração atual (Ollama local, 32 GB RAM)

```bash
AGENTS_LLM_PROVIDER=ollama
AGENTS_LLM_SMART_MODEL=qwen2.5:32b
AGENTS_LLM_FAST_MODEL=qwen2.5:14b
AGENTS_LLM_API_BASE=http://host.docker.internal:11434
AGENTS_LLM_API_KEY=
```

Ver [ADR 0005 — Ollama Qwen Provider](../adrs/0005-ollama-qwen-provider.md)
para o racional da escolha.

## Tabela comparativa (32 GB RAM, 8 GB VRAM)

| Modelo | Q4_K_M | Cabe VRAM 8GB | Forte em | Tempo/run (BR-FIN-MEX) |
|---|---:|---|---|---|
| `mistral-nemo:12b` | ~7 GB | ✅ | velocidade | **~8 min** (alucina números) |
| `qwen2.5:14b` | ~9 GB | ✅ (offload parcial) | instruction-following, JSON | ~12 min |
| `qwen2.5:32b` | ~20 GB | ❌ CPU offload | qualidade ~70B, baixa alucinação | **~20 min** ✅ usado |
| `command-r:35b` | ~22 GB | ❌ | citation grounding embutido | ~22 min |
| `gemma3:27b` | ~17 GB | ❌ | reasoning balanceado | ~18 min |
| `phi-4:14b` | ~9 GB | ✅ | math/STEM | ~12 min (16k contexto pode limitar) |

Recomendação:
- **Mínimo viável:** `qwen2.5:14b` smart+fast (drop-in, 12 min)
- **Qualidade alta:** `qwen2.5:32b` smart + `qwen2.5:14b` fast (atual)
- **Especialista citation:** trocar Citation Agent para `command-r:35b`
  (não implementado — exigiria split por agente)

## Trocar de modelo

### 1. Baixar modelo no Ollama do host

```bash
ollama pull qwen2.5:32b      # ~20 GB
ollama pull gemma3:27b       # ~17 GB
```

### 2. Editar `.env`

```bash
AGENTS_LLM_SMART_MODEL=gemma3:27b
```

### 3. Recriar container (não basta restart — env é parse-time)

```bash
docker compose up -d --force-recreate agents-server
docker compose exec agents-server env | grep AGENTS_LLM   # confirmar
```

### 4. (Opcional) Pré-aquecer

```bash
curl -s http://localhost:11434/api/generate \
  -d '{"model":"gemma3:27b","prompt":"ping","stream":false,"options":{"num_predict":1}}'
```

## Trocar de provider (ex.: Ollama → Anthropic)

```bash
# .env:
AGENTS_LLM_PROVIDER=anthropic
AGENTS_LLM_SMART_MODEL=claude-sonnet-4-5
AGENTS_LLM_FAST_MODEL=claude-haiku-4-5
AGENTS_LLM_API_KEY=sk-ant-...

docker compose up -d --force-recreate agents-server
```

Outros providers: `openai`, `gemini`, `groq`, `openrouter`. Exemplos em
`.env.example`. SDKs nativas são instaladas via extras opcionais
(`uv pip install -e ".[agents-anthropic]"`).

## Comportamento observado por modelo

### `mistral-nemo:12b` (descartado)

- **Tempo:** ~8 min/run
- **Problema raiz:** alucinação numérica forte. Inventa valores que não
  estão no contexto ("Brasil 4,7% PIB" quando dado real é 5,77%).
- **Documentado em:** [quality-assessment-2026-05-14](../quality-assessment-2026-05-14.md)

### `qwen2.5:32b` (atual)

- **Tempo:** ~20 min/run (CPU offload em máquina sem GPU dedicada)
- **Qualidade:** alta. Usa os números reais quando disponíveis.
- **Limitação:** ocasionalmente emite DOIs sintaticamente válidos mas
  inventados. Mitigação parcial via `is_real_doi` em
  [`agents/src/tools/rag_tools.py`](../../agents/src/tools/rag_tools.py).
- **Bug do Retriever:** não copia rows da tool para `primary_data`.
  Mitigação via auto-populate determinístico em
  [`agents/src/crews/analysis_crew.py`](../../agents/src/crews/analysis_crew.py)
  — ver [ADR 0006](../adrs/0006-retriever-autopopulate.md).

## Configuração recomendada de Ollama

No host (não no container):

```bash
# Variáveis de sistema (Windows: PowerShell admin)
setx OLLAMA_NUM_PARALLEL 1
setx OLLAMA_MAX_LOADED_MODELS 1
```

Evita dois runners simultâneos competindo por VRAM. Reinicie o serviço
Ollama após alterar.
