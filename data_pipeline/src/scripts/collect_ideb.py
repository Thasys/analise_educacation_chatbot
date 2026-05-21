"""CLI: coleta planilhas IDEB municipal do INEP e grava na Bronze.

O IDEB e divulgado bienalmente pelo INEP em planilhas XLSX no portal
``download.inep.gov.br/educacao_basica/portal_ideb/``. Cada planilha
``divulgacao_<etapa>_municipios_<ciclo>.xlsx`` cobre uma combinacao
(etapa, ciclo). A planilha do ciclo mais antigo trazido (2019 nesta
v1) traz toda a serie historica observada ate aquele ciclo, mais as
metas projetadas; a planilha do ciclo mais recente (2021) traz apenas
o observado do proprio ciclo.

Cobertura atual:

- AI (anos iniciais fund.): 2005-2021 via planilhas 2019 + 2021
- AF (anos finais fund.):    2005-2021 via planilhas 2019 + 2021
- EM (ensino medio):          2017-2021 via planilhas 2019 + 2021
   (EM municipal so passou a ser divulgado a partir de 2017)

Cada planilha vira um dataset bronze distinto, particionado por ciclo:
``data/bronze/inep/ideb_<etapa>/<ciclo>/data.parquet``. O staging dbt
(`stg_inep_ideb`) le todas via glob, faz UNPIVOT das colunas
`VL_OBSERVADO_*` e `VL_PROJECAO_*` e devolve schema canonico em formato
longo (1 linha por municipio, rede, etapa, ano).

Uso:

    cd data_pipeline
    uv run python -m src.scripts.collect_ideb               # baixa tudo
    uv run python -m src.scripts.collect_ideb --etapa AI    # so AI
    uv run python -m src.scripts.collect_ideb --ciclo 2021  # so 2021
"""

from __future__ import annotations

import argparse
import ssl
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
import pandas as pd
import truststore

from src.logging_config import get_logger
from src.utils.bronze import BronzeWriter
from src.utils.bulk_downloader import BulkDownloader

log = get_logger(__name__)


# Raiz do repo (..\..\..\..\ a partir deste arquivo). Usado como ancora
# para resolver `data/bronze/` e `data/_cache/` no layout do projeto,
# independente do CWD. `settings.bronze_root` resolve `./data/bronze`
# relativo ao CWD, que e correto quando o script roda na raiz mas
# escreve no lugar errado quando roda em `data_pipeline/` (gera
# `data_pipeline/data/bronze/...`).
_REPO_ROOT = Path(__file__).resolve().parents[3]


BASE_URL = (
    "https://download.inep.gov.br/educacao_basica/portal_ideb/"
    "planilhas_para_download/{ciclo}/divulgacao_{slug}_municipios_{ciclo}.xlsx"
)


@dataclass(frozen=True)
class IdebSpec:
    """Especificacao de uma planilha IDEB municipal (etapa x ciclo)."""

    etapa: str          # 'AI' | 'AF' | 'EM'
    ciclo: int          # 2019 | 2021
    url: str
    sheet_name: str
    header_row: int     # zero-indexed linha do cabecalho tecnico (SG_UF, ...)
    dataset: str        # bronze dataset slug


# Catalogo verificado em 2026-05-21 contra arquivos baixados via curl.
# Sheet names diferem entre AI/AF (`IDEB_<ET>_MUNICIPIOS`) e EM
# (`IDEB_Municipios (ENSINO MEDIO)`); ambos os ciclos usam o mesmo
# layout interno (cabecalho tecnico na linha 9, dados a partir da 10).
CATALOG: tuple[IdebSpec, ...] = (
    IdebSpec("AI", 2019, BASE_URL.format(ciclo=2019, slug="anos_iniciais"),
             "IDEB_AI_MUNICÍPIOS", 9, "ideb_anos_iniciais"),
    IdebSpec("AI", 2021, BASE_URL.format(ciclo=2021, slug="anos_iniciais"),
             "IDEB_AI_MUNICÍPIOS", 9, "ideb_anos_iniciais"),
    IdebSpec("AF", 2019, BASE_URL.format(ciclo=2019, slug="anos_finais"),
             "IDEB_AF_MUNICÍPIOS", 9, "ideb_anos_finais"),
    IdebSpec("AF", 2021, BASE_URL.format(ciclo=2021, slug="anos_finais"),
             "IDEB_AF_MUNICÍPIOS", 9, "ideb_anos_finais"),
    IdebSpec("EM", 2019, BASE_URL.format(ciclo=2019, slug="ensino_medio"),
             "IDEB_Municípios (ENSINO MÉDIO)", 9, "ideb_ensino_medio"),
    IdebSpec("EM", 2021, BASE_URL.format(ciclo=2021, slug="ensino_medio"),
             "IDEB_Municípios (ENSINO MÉDIO)", 9, "ideb_ensino_medio"),
)


def collect_one(
    spec: IdebSpec,
    *,
    downloader: BulkDownloader,
    writer: BronzeWriter,
) -> dict[str, Any]:
    """Baixa (com cache), parseia e grava uma planilha IDEB na Bronze."""
    log.info(
        "ideb.collect.start",
        etapa=spec.etapa,
        ciclo=spec.ciclo,
        url=spec.url,
    )
    download = downloader.download(spec.url)
    # `dtype=str` preserva exatamente o que o INEP publica (inclusive o
    # marcador '-' para missing). O cast para double acontece no staging
    # dbt via `safe_to_double`, que ja trata '-', '..', '' como NULL.
    # Bronze fica imutavel e auditavel; transformacoes ficam versionadas
    # em SQL.
    df = pd.read_excel(
        download.local_path,
        sheet_name=spec.sheet_name,
        header=spec.header_row,
        engine="openpyxl",
        dtype=str,
    )
    df.insert(0, "ETAPA", spec.etapa)
    df.insert(1, "CICLO_DIVULGACAO", str(spec.ciclo))
    result = writer.write(
        df,
        source="inep",
        dataset=spec.dataset,
        reference_period=str(spec.ciclo),
        source_url=spec.url,
        extra_metadata={
            "sheet_name": spec.sheet_name,
            "header_row": spec.header_row,
            "sha256_xlsx": download.sha256,
            "bytes_xlsx": download.bytes_downloaded,
        },
    )
    log.info(
        "ideb.collect.done",
        etapa=spec.etapa,
        ciclo=spec.ciclo,
        rows=result.row_count,
        cols=result.column_count,
        parquet=result.parquet_path,
    )
    return result.to_dict()


def _select_specs(
    catalog: tuple[IdebSpec, ...],
    *,
    etapa: str | None,
    ciclo: int | None,
) -> list[IdebSpec]:
    return [
        s for s in catalog
        if (etapa is None or s.etapa == etapa)
        and (ciclo is None or s.ciclo == ciclo)
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Baixa planilhas IDEB municipal do INEP para a Bronze.",
    )
    parser.add_argument(
        "--etapa", choices=("AI", "AF", "EM"),
        help="Filtra por etapa (default: todas).",
    )
    parser.add_argument(
        "--ciclo", type=int, choices=(2019, 2021),
        help="Filtra por ciclo de divulgacao (default: todos).",
    )
    parser.add_argument(
        "--cache-root",
        default=str(_REPO_ROOT / "data" / "_cache" / "inep" / "ideb"),
        help="Onde cachear os XLSX baixados.",
    )
    parser.add_argument(
        "--bronze-root",
        default=str(_REPO_ROOT / "data" / "bronze"),
        help="Raiz da camada Bronze (default: <repo>/data/bronze).",
    )
    args = parser.parse_args(argv)

    specs = _select_specs(CATALOG, etapa=args.etapa, ciclo=args.ciclo)
    if not specs:
        log.warning("ideb.collect.no_match", etapa=args.etapa, ciclo=args.ciclo)
        return 1

    # SSL context que delega a verificacao para o store de CAs do SO
    # (SChannel/WinTrust no Windows). Necessario porque
    # `download.inep.gov.br` serve cadeia via RNP ICPEdu (autoridade da
    # rede academica brasileira), ausente do bundle Mozilla do certifi.
    ssl_ctx = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    http_client = httpx.Client(timeout=600.0, verify=ssl_ctx)
    try:
        downloader = BulkDownloader(Path(args.cache_root), http_client=http_client)
        writer = BronzeWriter(Path(args.bronze_root))
        for spec in specs:
            collect_one(spec, downloader=downloader, writer=writer)
        log.info("ideb.collect.batch_done", total=len(specs))
        return 0
    finally:
        http_client.close()


if __name__ == "__main__":
    raise SystemExit(main())
