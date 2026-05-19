# Makefile — EduQuery
#
# Comandos curtos para tarefas comuns. Por enquanto cobre apenas a
# avaliacao empirica (`make evaluate`). Outras areas (dbt, frontend,
# api) tem comandos proprios em seus respectivos diretorios.
#
# Convencao: targets sao independentes de OS, mas alguns chamam
# Python via `python` direto. Em Windows + PowerShell isso resolve o
# `python` na PATH; em Linux/macOS resolve o `python3`. Em ambientes
# com varios Pythons, prefira rodar via `uv run python -m ...`.

.PHONY: help evaluate evaluate-unit evaluate-baseline evaluate-eduquery evaluate-redteam evaluate-report clean-evaluate-output

PY ?= python
GOLDEN_DIR := agents/evaluation/golden
OUTPUT_DIR := agents/evaluation/output

help:
	@echo "EduQuery — targets disponiveis:"
	@echo "  evaluate            Roda a bateria completa (Fase 2+; runners ainda stub)."
	@echo "  evaluate-unit       Roda apenas unit tests das metricas (Fase 1)."
	@echo "  evaluate-baseline   Roda o pipeline baseline (sem guardrails)."
	@echo "  evaluate-eduquery   Roda o pipeline completo (com guardrails)."
	@echo "  evaluate-redteam    Roda o conjunto adversarial."
	@echo "  evaluate-report     Gera paper_table.md a partir dos JSONs."
	@echo "  clean-evaluate-output   Remove $(OUTPUT_DIR)/."

evaluate-unit:
	cd agents && $(PY) -m pytest tests/evaluation -v

evaluate-baseline:
	@mkdir -p $(OUTPUT_DIR)
	cd agents && $(PY) -m evaluation.runners.run_baseline \
		--golden $(CURDIR)/$(GOLDEN_DIR) \
		--output $(CURDIR)/$(OUTPUT_DIR)/baseline.json

evaluate-eduquery:
	@mkdir -p $(OUTPUT_DIR)
	cd agents && $(PY) -m evaluation.runners.run_eduquery \
		--golden $(CURDIR)/$(GOLDEN_DIR) \
		--output $(CURDIR)/$(OUTPUT_DIR)/eduquery.json

evaluate-redteam:
	@mkdir -p $(OUTPUT_DIR)
	cd agents && $(PY) -m evaluation.runners.run_red_team \
		--golden $(CURDIR)/$(GOLDEN_DIR)/adversarial.yaml \
		--output $(CURDIR)/$(OUTPUT_DIR)/redteam.json

evaluate-report:
	cd agents && $(PY) -m evaluation.reports.generate_paper_table \
		--baseline $(CURDIR)/$(OUTPUT_DIR)/baseline.json \
		--eduquery $(CURDIR)/$(OUTPUT_DIR)/eduquery.json \
		--redteam  $(CURDIR)/$(OUTPUT_DIR)/redteam.json \
		--output   $(CURDIR)/$(OUTPUT_DIR)/paper_table.md

evaluate: evaluate-unit evaluate-baseline evaluate-eduquery evaluate-redteam evaluate-report

clean-evaluate-output:
	rm -rf $(OUTPUT_DIR)
