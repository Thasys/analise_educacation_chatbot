# ADR 0005 — Ollama + Qwen 2.5 como provider LLM primário

- **Status:** aceito
- **Data:** 2026-05-16
- **Fase:** pós-Fase 6 (operação)

## Contexto

O sistema usa LLMs em 8 agentes CrewAI (Orchestrator, Profiler, Retriever,
Statistician, Comparativist, Citation, Visualizer, Synthesizer). Restrições
de produto:

1. **Sem verba para APIs pagas** — Anthropic/OpenAI descartados.
2. **Hardware disponível:** 32 GB RAM + AMD RX 7600 (8 GB VRAM, ROCm).
3. **Privacidade dos dados** — embora as bases sejam públicas, o sistema é
   acadêmico on-premise.

Testes iniciais com `mistral-nemo:12b` (quality-assessment 2026-05-14)
documentaram alucinação numérica severa: 3/3 valores no markdown final
inventados pelo Synthesizer, mesmo com o contexto JSON correto disponível.

## Decisão

- **Provider:** `ollama` (rodando no host, OpenAI-compat em `:11434`).
- **Smart model** (Statistician, Comparativist, Synthesizer):
  **`qwen2.5:32b`** (Q4_K_M, ~20 GB) — usa offload CPU em máquina sem GPU
  dedicada, qualidade próxima a modelos 70B densos.
- **Fast model** (Orchestrator, Profiler, Retriever, Citation, Visualizer):
  **`qwen2.5:14b`** (Q4_K_M, ~9 GB) — cabe em VRAM 8 GB com offload parcial.

Configurado via `.env`:

```bash
AGENTS_LLM_PROVIDER=ollama
AGENTS_LLM_SMART_MODEL=qwen2.5:32b
AGENTS_LLM_FAST_MODEL=qwen2.5:14b
AGENTS_LLM_API_BASE=http://host.docker.internal:11434
```

## Alternativas consideradas

| Modelo | Por que não |
|---|---|
| `mistral-nemo:12b` | Alucinação numérica severa documentada |
| `gemma3:27b` | Reasoning ok mas menor instruction-following em PT-BR |
| `llama3.3:70b` | ~45 GB Q4 não cabe em 32 GB RAM |
| `mixtral:8x7b` | ~26 GB aperta os 32 GB; MoE com qualidade menor que qwen 32B denso |
| `command-r:35b` | Citation grounding embutido seria útil, mas exigiria split por agente (não modelo único smart/fast) |
| `phi-4:14b` | Forte em math/STEM mas contexto 16k limita Synthesizer com payload grande |

Anthropic Claude foi descartado pelo critério (1). Pode ser readicionado
como provider opcional sem refactor — a abstração `make_llm("smart"|"fast")`
em [`llm.py`](../../agents/src/llm.py) já é provider-agnóstica.

## Consequências

**Positivas:**
- Custo operacional zero além do hardware existente.
- Latência alta (~20 min para fluxo `data` completo) mas aceitável para
  sistema acadêmico on-premise.
- Reprodutibilidade total — modelo versionado por hash no Ollama.

**Negativas:**
- 2,5× mais lento que `mistral-nemo:12b` (~8 min) — esperado para offload CPU.
- Qwen 2.5 ainda emite ocasionalmente DOIs sintaticamente válidos mas
  inventados — mitigado por guardrail `is_real_doi` mas não eliminado.
- Bug observado: o Retriever em `qwen2.5:14b` chama a tool mas **não copia
  as rows** para `primary_data`. Mitigado por auto-populate determinístico
  ([ADR 0006](0006-retriever-autopopulate.md)).

**Débitos:**
- Caso o orçamento permita, considerar Anthropic Claude apenas para
  Synthesizer (mantendo os demais em Ollama) — equilíbrio entre custo e
  qualidade.
- Fine-tune de modelo pequeno (3-7B) especializado em Synthesizer educacional
  poderia eliminar alucinação residual sem custo recorrente. Estimativa:
  semanas de trabalho + dataset de pares (StatAnalysis JSON → markdown).

## Links

- Quality assessment original: [`quality-assessment-2026-05-14.md`](../quality-assessment-2026-05-14.md)
- Recomendações detalhadas: [`docs/operations/models-and-providers.md`](../operations/models-and-providers.md)
