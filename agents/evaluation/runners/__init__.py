"""Runners de avaliacao (Fase 1 = stubs).

Na Fase 2, os tres runners aqui implementam:

- `run_baseline.py`  pipeline RAG sem o Fact Checker / sem auto-populate
  do Retriever (baseline necessario para denominar a TIA).
- `run_eduquery.py`  pipeline completo (master_flow), com guardrails.
- `run_red_team.py`  consultas adversariais (`adversarial.yaml`).
"""
