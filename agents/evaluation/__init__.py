"""Avaliacao empirica do EduQuery.

Pacote que materializa o plano descrito em
`docs/evaluation/plano-avaliacao-empirica.md`. Contem:

- `golden/`     YAMLs versionados de gabaritos (factuais, comparativos,
                adversariais).
- `metrics/`    Funcoes puras (sem LLM) para medir acuracia numerica,
                validade de DOIs, cobertura de fontes, classificacao
                de alucinacao e a TIA (Taxa de Interceptacao de
                Alucinacoes).
- `runners/`    Stubs (Fase 1) que serao implementados na Fase 2 para
                rodar a bateria sobre o pipeline real.
- `reports/`    Geracao de tabela Markdown para o artigo.
"""
