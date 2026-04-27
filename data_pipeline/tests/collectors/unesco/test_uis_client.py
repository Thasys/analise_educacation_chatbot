"""Testes do coletor UNESCO UIS (SDMX-JSON 2.0)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import pandas as pd
import pyarrow.parquet as pq
import pytest

from src.collectors.unesco.uis_client import (
    UisCollector,
    make_edu_finance_collector,
    make_edu_non_finance_collector,
    make_sdg_collector,
)
from src.utils.bronze import BronzeWriter
from src.utils.ingestion_log import IngestionLogger


# ----------------------------------------------------------------------
# Fixture SDMX-JSON 2.0 mínimo (estrutura compatível com UIS)
# ----------------------------------------------------------------------
SAMPLE_SDMX: dict[str, Any] = {
    "data": {
        "structures": [
            {
                "dimensions": {
                    "series": [
                        {
                            "id": "REF_AREA",
                            "name": "Reference area",
                            "values": [
                                {"id": "BRA", "name": "Brazil"},
                                {"id": "USA", "name": "United States"},
                            ],
                        },
                        {
                            "id": "INDICATOR",
                            "name": "Indicator",
                            "values": [
                                {"id": "SE.PRM.NENR", "name": "Net enrolment, primary"}
                            ],
                        },
                    ],
                    "observation": [
                        {
                            "id": "TIME_PERIOD",
                            "name": "Time period",
                            "values": [
                                {"id": "2020"},
                                {"id": "2021"},
                                {"id": "2022"},
                            ],
                        }
                    ],
                },
                "attributes": {
                    "observation": [
                        {
                            "id": "OBS_STATUS",
                            "name": "Observation status",
                            "values": [{"id": "A"}, {"id": "E"}],
                        }
                    ]
                },
            }
        ],
        "dataSets": [
            {
                "series": {
                    # BRA (0), SE.PRM.NENR (0)
                    "0:0": {
                        "observations": {
                            "0": [95.5, 0],   # 2020, status A
                            "1": [96.0, 0],   # 2021, status A
                            "2": [96.4, 1],   # 2022, status E
                        }
                    },
                    # USA (1), SE.PRM.NENR (0)
                    "1:0": {
                        "observations": {
                            "0": [98.1, 0],
                            "2": [98.7, 1],
                        }
                    },
                }
            }
        ],
    }
}


# ----------------------------------------------------------------------
# Constructor / aliases
# ----------------------------------------------------------------------
def test_constructor_rejects_empty_flow_ref() -> None:
    with pytest.raises(ValueError):
        UisCollector(flow_ref="")


def test_apply_country_alias_to_empty_key() -> None:
    c = UisCollector(
        flow_ref="UNESCO,EDU_NON_FINANCE,1.0",
        countries="BRA",
        api_base="https://x/sdmx",
    )
    assert c.key == "BRA"


def test_apply_country_alias_overrides_first_key_segment() -> None:
    c = UisCollector(
        flow_ref="UNESCO,EDU_NON_FINANCE,1.0",
        key=".SE.PRM.NENR..",
        countries="BRA+USA",
        api_base="https://x/sdmx",
    )
    assert c.key == "BRA+USA.SE.PRM.NENR.."


def test_dataset_slug_from_flow_ref() -> None:
    c = UisCollector(flow_ref="UNESCO,EDU_NON_FINANCE,1.0", api_base="https://x/sdmx")
    assert c.dataset == "flow_unesco_edu_non_finance_1_0"


# ----------------------------------------------------------------------
# build_url
# ----------------------------------------------------------------------
def test_build_url_no_period() -> None:
    c = UisCollector(flow_ref="UNESCO,EDU_NON_FINANCE,1.0", api_base="https://x/sdmx")
    url = c.build_url(None)
    assert url.startswith("https://x/sdmx/data/UNESCO,EDU_NON_FINANCE,1.0/?")
    assert "dimensionAtObservation=AllDimensions" in url
    assert "format=jsondata" in url
    assert "startPeriod" not in url


def test_build_url_single_year_sets_both_bounds() -> None:
    c = UisCollector(flow_ref="UNESCO,EDU_NON_FINANCE,1.0", api_base="https://x/sdmx")
    url = c.build_url(2022)
    assert "startPeriod=2022" in url
    assert "endPeriod=2022" in url


def test_build_url_year_range() -> None:
    c = UisCollector(flow_ref="UNESCO,EDU_NON_FINANCE,1.0", api_base="https://x/sdmx")
    url = c.build_url("2010-2023")
    assert "startPeriod=2010" in url
    assert "endPeriod=2023" in url


def test_build_url_all_skips_period() -> None:
    c = UisCollector(flow_ref="UNESCO,EDU_NON_FINANCE,1.0", api_base="https://x/sdmx")
    url = c.build_url("all")
    assert "startPeriod" not in url
    assert "endPeriod" not in url


def test_build_url_includes_country_key() -> None:
    c = UisCollector(
        flow_ref="UNESCO,EDU_NON_FINANCE,1.0",
        countries="BRA",
        api_base="https://x/sdmx",
    )
    url = c.build_url(2022)
    assert "/data/UNESCO,EDU_NON_FINANCE,1.0/BRA?" in url


# ----------------------------------------------------------------------
# parse_sdmx_json
# ----------------------------------------------------------------------
def test_parse_sdmx_json_flattens_series_and_observations() -> None:
    df = UisCollector.parse_sdmx_json(SAMPLE_SDMX)
    # 3 obs para BRA + 2 obs para USA = 5 linhas
    assert len(df) == 5
    assert {"REF_AREA", "INDICATOR", "TIME_PERIOD", "OBS_VALUE", "OBS_STATUS"} <= set(df.columns)

    bra_2020 = df[(df["REF_AREA"] == "BRA") & (df["TIME_PERIOD"] == "2020")]
    assert bra_2020["OBS_VALUE"].iloc[0] == 95.5
    assert bra_2020["OBS_STATUS"].iloc[0] == "A"

    bra_2022 = df[(df["REF_AREA"] == "BRA") & (df["TIME_PERIOD"] == "2022")]
    assert bra_2022["OBS_STATUS"].iloc[0] == "E"


def test_parse_sdmx_json_obs_value_is_numeric() -> None:
    df = UisCollector.parse_sdmx_json(SAMPLE_SDMX)
    assert pd.api.types.is_numeric_dtype(df["OBS_VALUE"])


def test_parse_sdmx_json_handles_missing_attribute_index() -> None:
    payload = {
        "data": {
            "structures": [
                {
                    "dimensions": {
                        "series": [
                            {
                                "id": "REF_AREA",
                                "values": [{"id": "BRA"}],
                            }
                        ],
                        "observation": [
                            {"id": "TIME_PERIOD", "values": [{"id": "2020"}]}
                        ],
                    },
                    "attributes": {
                        "observation": [
                            {"id": "OBS_STATUS", "values": [{"id": "A"}]}
                        ]
                    },
                }
            ],
            "dataSets": [
                {
                    "series": {
                        "0": {"observations": {"0": [50.0, None]}}
                    }
                }
            ],
        }
    }
    df = UisCollector.parse_sdmx_json(payload)
    assert len(df) == 1
    assert df["OBS_VALUE"].iloc[0] == 50.0
    assert pd.isna(df["OBS_STATUS"].iloc[0])


def test_parse_sdmx_json_empty_dataset_returns_empty_df() -> None:
    df = UisCollector.parse_sdmx_json({"data": {"structures": [], "dataSets": []}})
    assert df.empty


def test_parse_sdmx_json_tolerates_missing_data_wrapper() -> None:
    """Alguns endpoints servem o conteúdo sem o wrapper {'data': ...}."""
    payload_unwrapped = SAMPLE_SDMX["data"]
    df = UisCollector.parse_sdmx_json(payload_unwrapped)  # type: ignore[arg-type]
    assert len(df) == 5


# ----------------------------------------------------------------------
# fetch
# ----------------------------------------------------------------------
def _mock_client(payload: Any) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_fetch_returns_dataframe_and_url() -> None:
    client = _mock_client(SAMPLE_SDMX)
    c = UisCollector(
        flow_ref="UNESCO,EDU_NON_FINANCE,1.0",
        countries="BRA+USA",
        api_base="https://x/sdmx",
        http_client=client,
    )
    df, url = c.fetch(reference_period="2020-2022")
    client.close()

    assert isinstance(df, pd.DataFrame)
    assert len(df) == 5
    assert "/data/UNESCO,EDU_NON_FINANCE,1.0/BRA+USA?" in url


def test_fetch_raises_on_http_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    c = UisCollector(
        flow_ref="UNESCO,EDU_NON_FINANCE,1.0",
        api_base="https://x/sdmx",
        http_client=client,
    )
    with pytest.raises(httpx.HTTPStatusError):
        c.fetch(reference_period="2020")
    client.close()


# ----------------------------------------------------------------------
# collect — pipeline completo
# ----------------------------------------------------------------------
def test_collect_writes_to_bronze(
    tmp_bronze_root: Path,
    disabled_ingestion_logger: IngestionLogger,
) -> None:
    client = _mock_client(SAMPLE_SDMX)
    c = UisCollector(
        flow_ref="UNESCO,EDU_NON_FINANCE,1.0",
        api_base="https://x/sdmx",
        http_client=client,
        bronze_writer=BronzeWriter(tmp_bronze_root),
        ingestion_logger=disabled_ingestion_logger,
    )
    result = c.collect(reference_period="2020-2022")
    client.close()

    expected_dir = (
        tmp_bronze_root / "unesco" / "flow_unesco_edu_non_finance_1_0" / "2020-2022"
    )
    assert (expected_dir / "data.parquet").exists()
    assert (expected_dir / "_metadata.json").exists()
    assert result.row_count == 5

    table = pq.read_table(result.parquet_path)
    assert "REF_AREA" in table.column_names
    assert "TIME_PERIOD" in table.column_names
    assert "OBS_VALUE" in table.column_names


# ----------------------------------------------------------------------
# Conveniências
# ----------------------------------------------------------------------
def test_make_edu_non_finance_collector() -> None:
    c = make_edu_non_finance_collector()
    assert c.flow_ref == "UNESCO,EDU_NON_FINANCE,1.0"
    assert c.dataset == "flow_unesco_edu_non_finance_1_0"
    assert c.source == "unesco"


def test_make_edu_finance_collector() -> None:
    c = make_edu_finance_collector()
    assert c.flow_ref == "UNESCO,EDU_FINANCE,1.0"


def test_make_sdg_collector() -> None:
    c = make_sdg_collector()
    assert c.flow_ref == "UNESCO,SDG,1.0"
