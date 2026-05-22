# Makefile — EduQuery
#
# Avaliacao empirica com 3 perfis de execucao (Secao 4.1 das
# orientacoes_metodologicas 2026-05-21):
#
#   smoke       10 itens in-scope        ~$3 / ~20min       (commit/PR)
#   official    84 itens, n=1            ~$27 / ~4h30min    (submissao)
#   publication 84 itens, n=3            ~$80 / ~13h        (camera-ready)
#
# Default provider: Anthropic. Override via env (`AGENTS_LLM_PROVIDER=ollama
# make evaluate-smoke` para rodar local sem custo, com latencia ~10x maior).

.PHONY: help \
	evaluate evaluate-unit \
	evaluate-smoke evaluate-official evaluate-publication \
	evaluate-baseline evaluate-eduquery evaluate-redteam evaluate-report \
	evaluate-tcc evaluate-tcc-with-llm \
	clean-evaluate-output

PY ?= python
GOLDEN_DIR := agents/evaluation/golden
OUTPUT_DIR := agents/evaluation/output

# Anthropic defaults (override no .env ou inline)
PROVIDER ?= anthropic
SMART ?= claude-sonnet-4-5
FAST ?= claude-haiku-4-5

help:
	@echo "EduQuery — Avaliacao empirica"
	@echo
	@echo "Perfis de execucao:"
	@echo "  evaluate-smoke         10 itens in-scope, n=1   (~\$$3, 20 min)"
	@echo "  evaluate-official      84 itens, n=1            (~\$$27, 4h30min)"
	@echo "  evaluate-publication   84 itens, n=3            (~\$$80, 13h)"
	@echo
	@echo "Etapas individuais:"
	@echo "  evaluate-unit          Roda os 119 unit tests das metricas (offline, 0.5s)"
	@echo "  evaluate-baseline      Pipeline baseline (sem guardrails)"
	@echo "  evaluate-eduquery      Pipeline completo (com guardrails)"
	@echo "  evaluate-redteam       Apenas adversarial.yaml"
	@echo "  evaluate-report        Gera paper_table.md"
	@echo
	@echo "TCC (Taxa de Comportamento Correto) — re-analise de JSONs existentes:"
	@echo "  evaluate-tcc           Camadas 1+2 (estrutural + semantica), custo \$$0"
	@echo "  evaluate-tcc-with-llm  Camadas 1+2+3 (inclui LLM juiz via Batch API, ~\$$0.025)"
	@echo
	@echo "Utilitarios:"
	@echo "  clean-evaluate-output  Remove $(OUTPUT_DIR)/"

# ----------------------------------------------------------------------
# Unit tests (offline, sem custo)
# ----------------------------------------------------------------------

evaluate-unit:
	cd agents && $(PY) -m pytest tests/evaluation -v

# ----------------------------------------------------------------------
# Perfis de execucao
# ----------------------------------------------------------------------

# smoke: 10 itens in-scope (Acao #3 das orientacoes do orientador).
# Brasil GASTO_EDU_PIB + LITERACY_15M.
evaluate-smoke: evaluate-unit
	@mkdir -p $(OUTPUT_DIR)/smoke
	cd agents && AGENTS_LLM_PROVIDER=$(PROVIDER) \
		AGENTS_LLM_SMART_MODEL=$(SMART) AGENTS_LLM_FAST_MODEL=$(FAST) \
		$(PY) -m evaluation.runners.run_eduquery \
		--golden $(CURDIR)/$(GOLDEN_DIR) \
		--output $(CURDIR)/$(OUTPUT_DIR)/smoke/eduquery.json \
		--limit 10

# official: bateria oficial n=1 (mesma da Fase 3 inicial)
evaluate-official: evaluate-baseline evaluate-eduquery evaluate-tcc evaluate-report

# publication: bateria com n=3 (revisao final para camera-ready)
evaluate-publication: evaluate-unit
	@mkdir -p $(OUTPUT_DIR)/publication
	cd agents && AGENTS_LLM_PROVIDER=$(PROVIDER) \
		AGENTS_LLM_SMART_MODEL=$(SMART) AGENTS_LLM_FAST_MODEL=$(FAST) \
		$(PY) -m evaluation.runners.run_eduquery \
		--golden $(CURDIR)/$(GOLDEN_DIR) \
		--output $(CURDIR)/$(OUTPUT_DIR)/publication/eduquery_run.json \
		--repetitions 3

# ----------------------------------------------------------------------
# Etapas individuais
# ----------------------------------------------------------------------

evaluate-baseline:
	@mkdir -p $(OUTPUT_DIR)
	cd agents && AGENTS_LLM_PROVIDER=$(PROVIDER) \
		AGENTS_LLM_SMART_MODEL=$(SMART) AGENTS_LLM_FAST_MODEL=$(FAST) \
		$(PY) -m evaluation.runners.run_baseline \
		--golden $(CURDIR)/$(GOLDEN_DIR) \
		--output $(CURDIR)/$(OUTPUT_DIR)/baseline_official.json

evaluate-eduquery:
	@mkdir -p $(OUTPUT_DIR)
	cd agents && AGENTS_LLM_PROVIDER=$(PROVIDER) \
		AGENTS_LLM_SMART_MODEL=$(SMART) AGENTS_LLM_FAST_MODEL=$(FAST) \
		$(PY) -m evaluation.runners.run_eduquery \
		--golden $(CURDIR)/$(GOLDEN_DIR) \
		--output $(CURDIR)/$(OUTPUT_DIR)/eduquery_official.json

evaluate-redteam:
	@mkdir -p $(OUTPUT_DIR)
	cd agents && AGENTS_LLM_PROVIDER=$(PROVIDER) \
		AGENTS_LLM_SMART_MODEL=$(SMART) AGENTS_LLM_FAST_MODEL=$(FAST) \
		$(PY) -m evaluation.runners.run_red_team \
		--golden $(CURDIR)/$(GOLDEN_DIR)/adversarial.yaml \
		--output $(CURDIR)/$(OUTPUT_DIR)/redteam.json

evaluate-report:
	cd agents && $(PY) -m evaluation.reports.generate_paper_table \
		--baseline $(CURDIR)/$(OUTPUT_DIR)/baseline_official.json \
		--eduquery $(CURDIR)/$(OUTPUT_DIR)/eduquery_official.json \
		--output   $(CURDIR)/$(OUTPUT_DIR)/paper_table.md

# ----------------------------------------------------------------------
# TCC (Taxa de Comportamento Correto) — re-analise sem custo de pipeline
# ----------------------------------------------------------------------

evaluate-tcc:
	cd agents && $(PY) -m evaluation.shared.reclassify_adversarials \
		--input $(CURDIR)/$(OUTPUT_DIR)/eduquery_official.json \
		--golden $(CURDIR)/$(GOLDEN_DIR)

evaluate-tcc-with-llm:
	cd agents && $(PY) -m evaluation.shared.reclassify_adversarials \
		--input $(CURDIR)/$(OUTPUT_DIR)/eduquery_official.json \
		--golden $(CURDIR)/$(GOLDEN_DIR) \
		--enable-llm-judge

# Alias historico (mantem compatibilidade)
evaluate: evaluate-official

clean-evaluate-output:
	rm -rf $(OUTPUT_DIR)
