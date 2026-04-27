"""Testes do coletor OCDE (SDMX REST + SDMX-JSON 2.0)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import pandas as pd
import pyarrow.parquet as pq
import pytest

from src.collectors.oecd.sdmx_client import (
    OecdSdmxCollector,
    make_eag_attainment_collector,
    make_eag_finance_collector,
)
from src.utils.bronze import BronzeWriter
from src.utils.ingestion_log import IngestionLogger


# Mesma estrutura SDMX-JSON 2.0 do UIS (parser é compartilhado).
SAMPLE_SDMX: dict[str, Any] = {
    "data": {
        "structures": [
            {
                "dimensions": {
                    "series": [
                        {
                            "id": "REF_AREA",
                            "values": [
                                {"id": "BRA"},
                                {"id": "USA"},
                                {"id": "FIN"},
                            ],
                        },
                        {"id": "MEASURE", "values": [{"id": "EXP_PER_STUDENT"}]},
                    ],
                    "observation": [
                        {
                            "id": "TIME_PERIOD",
                            "values": [{"id": "2020"}, {"id": "2021"}],
                        }
                    ],
                },
                "attributes": {"observation": []},
            }
        ],
        "dataSets": [
            {
                "series": {
                    "0:0": {"observations": {"0": [4500.0], "1": [4700.0]}},
                    "1:0": {"observations": {"0": [13000.0], "1": [13500.0]}},
                    "2:0": {"observations": {"0": [11000.0], "1": [11200.0]}},
                }
            }
        ],
    }
}


# ----------------------------------------------------------------------
# Constructor
# ----------------------------------------------------------------------
def test_constructor_rejects_empty_flow_ref() -> None:
    with pytest.raises(ValueError):
        OecdSdmxCollector(flow_ref="")


def test_dataset_slug_normalises_separators() -> None:
    """A slug do dataset substitui ',', '.' e '@' por '_' e baixa caixa."""
    c = OecdSdmxCollector(
        flow_ref="OECD.EDU.IMEP,DSD_EAG_FIN@DF_FIN_PERSTUDENT,1.0",
        api_base="https://x/rest",
    )
    assert c.dataset == "flow_oecd_edu_imep_dsd_eag_fin_df_fin_perstudent_1_0"


def test_apply_country_alias_to_empty_key() -> None:
    c = OecdSdmxCollector(
        flow_ref="OECD.X,Y,1.0", countries="BRA", api_base="https://x/rest"
    )
    assert c.key == "BRA"


def test_apply_country_alias_overrides_first_segment() -> None:
    c = OecdSdmxCollector(
        flow_ref="OECD.X,Y,1.0",
        key=".EXP_PER_STUDENT..",
        countries="BRA+USA",
        api_base="https://x/rest",
    )
    assert c.key == "BRA+USA.EXP_PER_STUDENT.."


# ----------------------------------------------------------------------
# build_url
# ----------------------------------------------------------------------
def test_build_url_no_period() -> None:
    c = OecdSdmxCollector(
        flow_ref="OECD.X,Y,1.0", api_base="https://sdmx.oecd.org/public/rest"
    )
    url = c.build_url(None)
    assert url.startswith("https://sdmx.oecd.org/public/rest/data/OECD.X,Y,1.0/?")
    assert "dimensionAtObservation=AllDimensions" in url
    assert "format=jsondata" in url
    assert "startPeriod" not in url


def test_build_url_with_year_range() -> None:
    c = OecdSdmxCollector(
        flow_ref="OECD.X,Y,1.0", api_base="https://sdmx.oecd.org/public/rest"
    )
    url = c.build_url("2018-2022")
    assert "startPeriod=2018" in url
    assert "endPeriod=2022" in url


def test_build_url_with_single_year_sets_both_bounds() -> None:
    c = OecdSdmxCollector(
        flow_ref="OECD.X,Y,1.0", api_base="https://sdmx.oecd.org/public/rest"
    )
    url = c.build_url(2022)
    assert "startPeriod=2022" in url
    assert "endPeriod=2022" in url


def test_build_url_with_country_key() -> None:
    c = OecdSdmxCollector(
        flow_ref="OECD.X,Y,1.0",
        countries="BRA",
        api_base="https://sdmx.oecd.org/public/rest",
    )
    url = c.build_url(2022)
    assert "/data/OECD.X,Y,1.0/BRA?" in url


# ----------------------------------------------------------------------
# fetch (parser delegado a utils.sdmx_json — só validamos integração)
# ----------------------------------------------------------------------
def _mock_client(payload: Any) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_fetch_returns_parsed_dataframe() -> None:
    client = _mock_client(SAMPLE_SDMX)
    c = OecdSdmxCollector(
        flow_ref="OECD.EDU.IMEP,DSD_EAG_FIN@DF_FIN_PERSTUDENT,1.0",
        countries="BRA+USA+FIN",
        api_base="https://sdmx.oecd.org/public/rest",
        http_client=client,
    )
    df, url = c.fetch(reference_period="2020-2021")
    client.close()

    # 3 países × 2 anos × 1 medida = 6 linhas
    assert len(df) == 6
    assert {"REF_AREA", "MEASURE", "TIME_PERIOD", "OBS_VALUE"} <= set(df.columns)
    bra_2020 = df[(df["REF_AREA"] == "BRA") & (df["TIME_PERIOD"] == "2020")]
    assert bra_2020["OBS_VALUE"].iloc[0] == 4500.0
    assert "/data/OECD.EDU.IMEP" in url


def test_fetch_raises_on_http_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429)  # rate limit OCDE

    client = httpx.Client(transport=httpx.MockTransport(handler))
    c = OecdSdmxCollector(
        flow_ref="OECD.X,Y,1.0",
        api_base="https://sdmx.oecd.org/public/rest",
        http_client=client,
    )
    with pytest.raises(httpx.HTTPStatusError):
        c.fetch(reference_period="2022")
    client.close()


# ----------------------------------------------------------------------
# collect — pipeline completo
# ----------------------------------------------------------------------
def test_collect_writes_to_bronze(
    tmp_bronze_root: Path,
    disabled_ingestion_logger: IngestionLogger,
) -> None:
    client = _mock_client(SAMPLE_SDMX)
    c = OecdSdmxCollector(
        flow_ref="OECD.EDU.IMEP,DSD_EAG_FIN@DF_FIN_PERSTUDENT,1.0",
        api_base="https://sdmx.oecd.org/public/rest",
        http_client=client,
        bronze_writer=BronzeWriter(tmp_bronze_root),
        ingestion_logger=disabled_ingestion_logger,
    )
    result = c.collect(reference_period="2020-2021")
    client.close()

    expected_dir = (
        tmp_bronze_root
        / "oecd"
        / "flow_oecd_edu_imep_dsd_eag_fin_df_fin_perstudent_1_0"
        / "2020-2021"
    )
    assert (expected_dir / "data.parquet").exists()
    assert result.row_count == 6

    table = pq.read_table(result.parquet_path)
    assert "REF_AREA" in table.column_names
    assert "OBS_VALUE" in table.column_names


# ----------------------------------------------------------------------
# Conveniências
# ----------------------------------------------------------------------
def test_make_eag_finance_collector() -> None:
    c = make_eag_finance_collector()
    assert c.flow_ref == "OECD.EDU.IMEP,DSD_EAG_FIN@DF_FIN_PERSTUDENT,1.0"
    assert c.source == "oecd"


def test_make_eag_attainment_collector() -> None:
    c = make_eag_attainment_collector()
    assert "DSD_EAG_NEAC" in c.flow_ref
