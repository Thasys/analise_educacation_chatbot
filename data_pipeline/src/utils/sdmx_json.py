"""Parser SDMX-JSON 2.0 → DataFrame longo.

Compartilhado entre coletores que falam SDMX-JSON 2.0 (UNESCO UIS, OCDE).

Estrutura típica:

    payload["data"]["structures"][0]["dimensions"]["series"]      [list]
                                    ["dimensions"]["observation"] [list]
                                    ["attributes"]["observation"] [list]
    payload["data"]["dataSets"][0]["series"]
                                  [<series_key>]["observations"]
                                                [<obs_key>] = [value, attr_idx0, ...]

`series_key`: índices das dimensões `series` separados por `:`.
`obs_key`:    índices das dimensões `observation` separados por `:`.
Atributos da observação são valores indexados na lista de `attributes.observation`.

A função tolera payloads sem o wrapper `{"data": ...}` (alguns endpoints
servem o conteúdo diretamente).
"""

from __future__ import annotations

from typing import Any

import pandas as pd


def parse_sdmx_json(payload: dict[str, Any]) -> pd.DataFrame:
    """Achata um payload SDMX-JSON 2.0 em DataFrame longo.

    Saída: uma linha por observação com colunas iguais aos `id`s das
    dimensões + `OBS_VALUE` (numérico) + atributos resolvidos por id.
    """
    data = payload.get("data") or payload
    structures = data.get("structures") or []
    datasets = data.get("dataSets") or []
    if not structures or not datasets:
        return pd.DataFrame(columns=["TIME_PERIOD", "OBS_VALUE"])

    structure = structures[0]
    series_dims = structure.get("dimensions", {}).get("series", []) or []
    obs_dims = structure.get("dimensions", {}).get("observation", []) or []
    obs_attrs = structure.get("attributes", {}).get("observation", []) or []

    series_dim_ids = [d.get("id", f"DIM_{i}") for i, d in enumerate(series_dims)]
    obs_dim_ids = [d.get("id", f"OBS_{i}") for i, d in enumerate(obs_dims)]
    obs_attr_ids = [a.get("id", f"ATTR_{i}") for i, a in enumerate(obs_attrs)]

    series_value_lookups = [
        [v.get("id") for v in (d.get("values") or [])] for d in series_dims
    ]
    obs_value_lookups = [
        [v.get("id") for v in (d.get("values") or [])] for d in obs_dims
    ]
    obs_attr_lookups = [
        [v.get("id") for v in (a.get("values") or [])] for a in obs_attrs
    ]

    rows: list[dict[str, Any]] = []
    series_map = datasets[0].get("series") or {}
    for series_key, series_payload in series_map.items():
        series_indices = [int(x) for x in str(series_key).split(":") if x != ""]
        series_values = {
            series_dim_ids[i]: series_value_lookups[i][idx]
            if i < len(series_value_lookups) and idx < len(series_value_lookups[i])
            else None
            for i, idx in enumerate(series_indices)
        }
        observations = series_payload.get("observations") or {}
        for obs_key, obs_payload in observations.items():
            obs_indices = [int(x) for x in str(obs_key).split(":") if x != ""]
            obs_values = {
                obs_dim_ids[i]: obs_value_lookups[i][idx]
                if i < len(obs_value_lookups) and idx < len(obs_value_lookups[i])
                else None
                for i, idx in enumerate(obs_indices)
            }

            value = obs_payload[0] if obs_payload else None
            attr_values: dict[str, Any] = {}
            for i, attr_id in enumerate(obs_attr_ids):
                raw_idx = obs_payload[i + 1] if i + 1 < len(obs_payload) else None
                if raw_idx is None or raw_idx == "":
                    attr_values[attr_id] = None
                else:
                    try:
                        idx = int(raw_idx)
                        lookup = obs_attr_lookups[i] if i < len(obs_attr_lookups) else []
                        attr_values[attr_id] = lookup[idx] if idx < len(lookup) else None
                    except (TypeError, ValueError):
                        attr_values[attr_id] = raw_idx

            rows.append(
                {**series_values, **obs_values, "OBS_VALUE": value, **attr_values}
            )

    if not rows:
        cols = series_dim_ids + obs_dim_ids + ["OBS_VALUE"] + obs_attr_ids
        return pd.DataFrame(columns=cols or ["TIME_PERIOD", "OBS_VALUE"])

    df = pd.DataFrame(rows)
    if "OBS_VALUE" in df.columns:
        df["OBS_VALUE"] = pd.to_numeric(df["OBS_VALUE"], errors="coerce")
    return df
