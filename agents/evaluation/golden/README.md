# Golden datasets — EduQuery

Esta pasta contem gabaritos versionados para a avaliacao empirica
descrita em [`docs/evaluation/plano-avaliacao-empirica.md`](../../../docs/evaluation/plano-avaliacao-empirica.md).

## Arquivos

| Arquivo | Conteudo | Tamanho minimo | Status |
|---|---|---:|---|
| `queries_factuais.yaml` | Perguntas com 1 valor numerico esperado | 30 | 32 itens DRAFT |
| `queries_comparativas.yaml` | Perguntas com 2+ valores (Brasil vs OCDE / paises) | 20 | 22 itens DRAFT |
| `adversarial.yaml` | Conjunto de red teaming (9 categorias) | 30 (>=3 por categoria) | 30 itens DRAFT |
| `per_agent/` | Gabaritos especificos por agente CrewAI | — | criado vazio (Fase 2+) |

**Total Fase 1: 84 itens.**

## Protocolo de verificacao (DRAFT -> VERIFIED)

Todos os itens iniciam com `_verified: false` no YAML. Antes do run
oficial da Fase 3, **cada item DEVE ser cross-checado** contra a
fonte primaria declarada em `primary_source`. O criterio de aceite:

1. Pesquisar o valor na fonte oficial (URL ou DOI declarado).
2. Validar que o valor cai dentro da `tolerance_pct` declarada.
3. Se divergente, ajustar `expected_value` (ou remover o item).
4. Mudar `_verified: false` -> `_verified: true`.
5. Itens sem fonte verificavel devem ser **removidos**, nao mantidos
   com valor especulativo (Secao 2.1 dos principios inegociaveis).

A Fase 1 deixa o protocolo definido mas nao executa a verificacao;
isso ocorre antes do run oficial (Fase 3).

## Categorias adversariais (9 canonicas)

Definidas na Secao 6 do plano mestre:

1. `adversarial_numbers`        ano/valor impossivel
2. `doi_fishing`                DOI inventado
3. `source_spoofing`            fonte fora do RAG
4. `year_confusion`             ano implausivel ou misturado
5. `cross_source_contradiction` IBGE vs OECD divergentes
6. `privacy_probe`              dado pessoal/identificavel
7. `prompt_injection`           tentativa de bypass
8. `empty_rag`                  fora do escopo coberto
9. `adversarial_figure`         pedido com spec malformado

**Cada categoria tem >=3 itens** no `adversarial.yaml` (regra do plano).

## Como adicionar itens novos

1. Decidir arquivo (factual / comparativo / adversarial).
2. Seguir o **schema** documentado no cabecalho do YAML.
3. Atribuir `id` proximo livre (F-NNN, C-NNN, A-NNN).
4. `_verified: false` inicialmente.
5. Rodar `python -m pytest agents/tests/evaluation/ -v` para validar
   que o `conftest` carrega o item sem erro.

## Como NAO adicionar itens

- Sem `primary_source` declarada -> nao serve para credibilidade
  academica.
- Com `expected_value` "achismo" sem citacao -> proibido pelo
  principio 1 do plano (nao inventar numeros).
- Itens duplicados entre arquivos -> nao misturar factual e
  adversarial.

## Vinculo com o artigo

Os 84 itens deste pacote alimentam:

- **Tabela da Secao 4 do artigo:** TIA, acuracia, recall, FP, latencia.
- **Breakdown por categoria adversarial:** tabela complementar
  mostrando taxa de bloqueio por categoria.

Ver `agents/evaluation/reports/generate_paper_table.py` (stub na
Fase 1; implementacao real na Fase 3).
