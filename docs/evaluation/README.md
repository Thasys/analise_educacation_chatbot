# Documentação de Avaliação Empírica — EduQuery

Esta pasta contém os planos e instruções para a avaliação empírica do
sistema EduQuery que alimenta a Seção 4 (Resultados) do artigo SBIE
2026 / Trilha TPIE.

## Conteúdo

- **[plano-avaliacao-empirica.md](./plano-avaliacao-empirica.md)** —
  Documento mestre. Auto-suficiente. Cobre: estado atual, princípios,
  plano por camada, golden datasets, métricas, red teaming,
  automação, cronograma, integração com o artigo, limitações.

- **[prompt-para-novo-chat.md](./prompt-para-novo-chat.md)** —
  Briefing pronto para colar em outra sessão de chat que vá
  implementar o plano. Contém contexto mínimo, regras inegociáveis e
  checklist faseado de execução.

## Estado

- Plano: **versão 1.0, aprovado em 2026-05-18**
- Implementação: **pendente** (Fase 1 não iniciada)
- Resultado no artigo: o placeholder `[X%]` no resumo será
  substituído após execução real da bateria

## Como começar

- Se você é o autor: ler o plano mestre e abrir uma nova sessão
  colando o conteúdo de `prompt-para-novo-chat.md`.
- Se você é um agente recebendo o trabalho: leia
  `prompt-para-novo-chat.md` primeiro (briefing), depois
  `plano-avaliacao-empirica.md` para os detalhes técnicos.

## Vínculo com o artigo

- Repositório do artigo: (mantido fora deste repo)
- Trilha: TPIE (Pesquisa em Informática na Educação), Qualis A3
- Prazos: registro de resumo no JEMS em 2026-05-18; upload PDF em
  2026-05-20; notificação de aceite em 2026-07-08
- Métrica principal a gerar: **TIA — Taxa de Interceptação de
  Alucinações** (substitui `[X%]` no resumo)
