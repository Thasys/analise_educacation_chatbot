"""Testes do coletor Eurostat (JSON-stat 2.0)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import pandas as pd
import pyarrow.parquet as pq
import pytest

from src.collectors.eurostat.jsonstat_client import (
    EurostatCollector,
    make_early_school_leavers_collector,
    make_education_expenditure_collector,
    make_enrolment_collector,
)
from src.utils.bronze import BronzeWriter
from src.utils.ingestion_log import IngestionLogger


# Cube 2 dimensões: geo (3 países) × time (2 anos) = 6 células.
SAMPLE_JSONSTAT: dict[str, Any] = {
    "version": "2.0",
    "class": "dataset",
    "label": "Test enrolment",
    "source": "Eurostat",
    "id": ["geo", "time"],
    "size": [3, 2],
    "dimension": {
        "geo": {
            "label": "Geo",
            "category": {
                "index": {"BE": 0, "DE": 1, "FR": 2},
                "label": {"BE": "Belgium", "DE": "Germany", "FR": "France"},
            },
        },
        "time": {
            "label": "Time",
            "category": {
                "index": {"2020": 0, "2021": 1},
                "label": {"2020": "2020", "2021": "2021"},
            },
        },
    },
    "value": [10.0, 11.0, 20.0, None, 30.0, 31.0],
    "status": {"3": ":"},  # célula DE/2021 marcada como ausente
}


# ----------------------------------------------------------------------
# Constructor
# ----------------------------------------------------------------------
def test_constructor_rejects_empty_dataset_code() -> None:
    with pytest.raises(ValueError):
        EurostatCollector(dataset_code="")


def test_dataset_slug_lowercased() -> None:
    c = EurostatCollector(
        dataset_code="EDUC_UOE_ENRT01", api_base="https://x/v1"
    )
    assert c.dataset == "dataset_educ_uoe_enrt01"


# ----------------------------------------------------------------------
# build_url
# ----------------------------------------------------------------------
def test_build_url_no_filters_no_period() -> None:
    c = EurostatCollector(
        dataset_code="educ_uoe_enrt01", api_base="https://ec.europa.eu/eurostat/api/v1"
    )
    url = c.build_url(None)
    assert url == "https://ec.europa.eu/eurostat/api/v1/data/educ_uoe_enrt01"


def test_build_url_with_list_filter_emits_repeated_keys() -> None:
    c = EurostatCollector(
        dataset_code="educ_uoe_enrt01",
        filters={"geo": ["BE", "DE", "FR"]},
        api_base="https://x/v1",
    )
    url = c.build_url(None)
    # cada par chave=valor é separado; urlencode preserva ordem
    assert url.count("geo=") == 3
    assert "geo=BE" in url and "geo=DE" in url and "geo=FR" in url


def test_build_url_single_year_uses_time() -> None:
    c = EurostatCollector(dataset_code="educ_uoe_enrt01", api_base="https://x/v1")
    url = c.build_url(2022)
    assert "time=2022" in url


def test_build_url_year_range_uses_since_until() -> None:
    c = EurostatCollector(dataset_code="educ_uoe_enrt01", api_base="https://x/v1")
    url = c.build_url("2010-2023")
    assert "sinceTimePeriod=2010" in url
    assert "untilTimePeriod=2023" in url


def test_build_url_period_overrides_time_in_filters() -> None:
    """Quando reference_period é dado, qualquer 'time' em filters é ignorado."""
    c = EurostatCollector(
        dataset_code="educ_uoe_enrt01",
        filters={"time": [2018, 2019]},
        api_base="https://x/v1",
    )
    url = c.build_url(2022)
    assert "time=2018" not in url
    assert "time=2019" not in url
    assert "time=2022" in url


def test_build_url_all_keeps_filters_but_skips_period() -> None:
    c = EurostatCollector(
        dataset_code="educ_uoe_enrt01",
        filters={"geo": "BE"},
        api_base="https://x/v1",
    )
    url = c.build_url("all")
    assert "geo=BE" in url
    assert "time=" not in url
    assert "sinceTimePeriod" not in url


# ----------------------------------------------------------------------
# parse_jsonstat
# ----------------------------------------------------------------------
def test_parse_jsonstat_dense_value_array() -> None:
    df = EurostatCollector.parse_jsonstat(SAMPLE_JSONSTAT)
    # 5 valores não-nulos (a célula DE/2021 é None)
    assert len(df) == 5
    assert {"geo", "time", "OBS_VALUE", "OBS_STATUS"} <= set(df.columns)
    be_2020 = df[(df["geo"] == "BE") & (df["time"] == "2020")]
    assert be_2020["OBS_VALUE"].iloc[0] == 10.0


def test_parse_jsonstat_row_major_order_is_correct() -> None:
    """Confirma decoding row-major: i=2 corresponde a (geo=DE, time=2020)."""
    df = EurostatCollector.parse_jsonstat(SAMPLE_JSONSTAT)
    # No SAMPLE: value[2] = 20.0, que corresponde a coords (1, 0) = (DE, 2020).
    de_2020 = df[(df["geo"] == "DE") & (df["time"] == "2020")]
    assert de_2020["OBS_VALUE"].iloc[0] == 20.0


def test_parse_jsonstat_status_attached_when_present() -> None:
    df = EurostatCollector.parse_jsonstat(SAMPLE_JSONSTAT)
    # status só foi setado em i=3 (DE/2021), que é null no value → é pulada.
    # Logo, OBS_STATUS deve existir como coluna mas estar vazia/NA nas linhas.
    assert "OBS_STATUS" in df.columns
    assert df["OBS_STATUS"].isna().all()


def test_parse_jsonstat_sparse_value_dict() -> None:
    payload = {
        **SAMPLE_JSONSTAT,
        "value": {"0": 10.0, "5": 31.0},  # apenas 2 células populadas
        "status": None,
    }
    df = EurostatCollector.parse_jsonstat(payload)
    assert len(df) == 2
    coords = set(zip(df["geo"], df["time"]))
    assert ("BE", "2020") in coords
    assert ("FR", "2021") in coords


def test_parse_jsonstat_empty_payload_returns_empty_df() -> None:
    df = EurostatCollector.parse_jsonstat({})
    assert df.empty


def test_parse_jsonstat_obs_value_is_numeric() -> None:
    df = EurostatCollector.parse_jsonstat(SAMPLE_JSONSTAT)
    assert pd.api.types.is_numeric_dtype(df["OBS_VALUE"])


# ----------------------------------------------------------------------
# fetch
# ----------------------------------------------------------------------
def _mock_client(payload: Any) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    return httpx.Client(transport=httpx.MockTransport(handler))


def test_fetch_returns_dataframe_and_url() -> None:
    client = _mock_client(SAMPLE_JSONSTAT)
    c = EurostatCollector(
        dataset_code="educ_uoe_enrt01",
        api_base="https://x/v1",
        http_client=client,
    )
    df, url = c.fetch(reference_period="2020-2021")
    client.close()

    assert len(df) == 5
    assert "/data/educ_uoe_enrt01?" in url
    assert "sinceTimePeriod=2020" in url


def test_fetch_raises_on_http_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    c = EurostatCollector(
        dataset_code="educ_uoe_enrt01",
        api_base="https://x/v1",
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
    client = _mock_client(SAMPLE_JSONSTAT)
    c = EurostatCollector(
        dataset_code="educ_uoe_enrt01",
        api_base="https://x/v1",
        http_client=client,
        bronze_writer=BronzeWriter(tmp_bronze_root),
        ingestion_logger=disabled_ingestion_logger,
    )
    result = c.collect(reference_period="2020-2021")
    client.close()

    expected_dir = (
        tmp_bronze_root / "eurostat" / "dataset_educ_uoe_enrt01" / "2020-2021"
    )
    assert (expected_dir / "data.parquet").exists()
    assert (expected_dir / "_metadata.json").exists()
    assert result.row_count == 5

    table = pq.read_table(result.parquet_path)
    assert "geo" in table.column_names
    assert "time" in table.column_names
    assert "OBS_VALUE" in table.column_names


# ----------------------------------------------------------------------
# Conveniências
# ----------------------------------------------------------------------
def test_make_enrolment_collector() -> None:
    c = make_enrolment_collector()
    assert c.dataset_code == "educ_uoe_enrt01"
    assert c.dataset == "dataset_educ_uoe_enrt01"
    assert c.source == "eurostat"


def test_make_education_expenditure_collector() -> None:
    c = make_education_expenditure_collector()
    assert c.dataset_code == "educ_uoe_fine01"


def test_make_early_school_leavers_collector() -> None:
    c = make_early_school_leavers_collector()
    assert c.dataset_code == "edat_lfse_14"
