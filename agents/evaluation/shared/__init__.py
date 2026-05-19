"""Utilidades compartilhadas entre os runners (Fase 2).

Centraliza:
- `loader`: carga e validacao dos YAMLs de golden.
- `parser`: extracao de numeros da resposta markdown.
- `runner`: laco principal que itera itens, invoca master_flow e
  serializa resultados em JSON.

Mantemos esses helpers separados dos `runners/run_*.py` para que cada
runner seja apenas uma `main()` curta — toda a logica testavel fica
aqui.
"""
