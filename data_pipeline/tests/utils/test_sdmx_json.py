"""Testes do parser SDMX-JSON 2.0 compartilhado entre UIS e OCDE."""

from __future__ import annotations

from typing import Any

import pandas as pd

from src.utils.sdmx_json import parse_sdmx_json


def _structure(
    *,
    series_dims: list[dict[str, Any]],
    obs_dims: list[dict[str, Any]],
    obs_attrs: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "dimensions": {"series": series_dims, "observation": obs_dims},
        "attributes": {"observation": obs_attrs or []},
    }


def test_parse_returns_empty_when_no_structures_or_datasets() -> None:
    assert parse_sdmx_json({}).empty
    assert parse_sdmx_json({"data": {"structures": [], "dataSets": []}}).empty


def test_parse_handles_single_series_single_obs() -> None:
    payload = {
        "data": {
            "structures": [
                _structure(
                    series_dims=[{"id": "REF_AREA", "values": [{"id": "BRA"}]}],
                    obs_dims=[{"id": "TIME_PERIOD", "values": [{"id": "2020"}]}],
                )
            ],
            "dataSets": [
                {"series": {"0": {"observations": {"0": [98.5]}}}}
            ],
        }
    }
    df = parse_sdmx_json(payload)
    assert len(df) == 1
    assert df["REF_AREA"].iloc[0] == "BRA"
    assert df["TIME_PERIOD"].iloc[0] == "2020"
    assert df["OBS_VALUE"].iloc[0] == 98.5


def test_parse_resolves_observation_attribute_indices_to_codes() -> None:
    payload = {
        "data": {
            "structures": [
                _structure(
                    series_dims=[{"id": "REF_AREA", "values": [{"id": "BRA"}]}],
                    obs_dims=[{"id": "TIME_PERIOD", "values": [{"id": "2020"}]}],
                    obs_attrs=[
                        {
                            "id": "OBS_STATUS",
                            "values": [{"id": "A"}, {"id": "E"}],
                        }
                    ],
                )
            ],
            "dataSets": [
                {"series": {"0": {"observations": {"0": [98.5, 1]}}}}
            ],
        }
    }
    df = parse_sdmx_json(payload)
    assert df["OBS_STATUS"].iloc[0] == "E"


def test_parse_unwraps_payload_without_data_key() -> None:
    """Alguns endpoints servem o conteúdo sem o wrapper {'data': ...}."""
    inner = {
        "structures": [
            _structure(
                series_dims=[{"id": "REF_AREA", "values": [{"id": "BRA"}]}],
                obs_dims=[{"id": "TIME_PERIOD", "values": [{"id": "2020"}]}],
            )
        ],
        "dataSets": [{"series": {"0": {"observations": {"0": [1.0]}}}}],
    }
    df = parse_sdmx_json(inner)
    assert len(df) == 1


def test_parse_obs_value_is_numeric_dtype() -> None:
    payload = {
        "data": {
            "structures": [
                _structure(
                    series_dims=[{"id": "REF_AREA", "values": [{"id": "BRA"}]}],
                    obs_dims=[{"id": "TIME_PERIOD", "values": [{"id": "2020"}]}],
                )
            ],
            "dataSets": [{"series": {"0": {"observations": {"0": ["3.14"]}}}}],
        }
    }
    df = parse_sdmx_json(payload)
    assert pd.api.types.is_numeric_dtype(df["OBS_VALUE"])
    assert df["OBS_VALUE"].iloc[0] == 3.14
