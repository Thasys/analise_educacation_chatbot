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
    dataset0 = datasets[0]

    def _parse_obs_payload(
        obs_payload: list[Any] | None,
    ) -> tuple[Any, dict[str, Any]]:
        """Resolve [value, attr_idx_0, attr_idx_1, ...] em (value, attrs_resolved)."""
        if not obs_payload:
            return None, {a: None for a in obs_attr_ids}
        value = obs_payload[0]
        attr_values: dict[str, Any] = {}
        for i, attr_id in enumerate(obs_attr_ids):
            raw_idx = obs_payload[i + 1] if i + 1 < len(obs_payload) else None
            if raw_idx is None or raw_idx == "":
                attr_values[attr_id] = None
                continue
            try:
                idx = int(raw_idx)
                lookup = obs_attr_lookups[i] if i < len(obs_attr_lookups) else []
                attr_values[attr_id] = lookup[idx] if idx < len(lookup) else None
            except (TypeError, ValueError):
                attr_values[attr_id] = raw_idx
        return value, attr_values

    # Layout A — `dimensionAtObservation=TIME_PERIOD` (default antigo):
    # series ficam nivel acima, observation contem so a dimensao temporal.
    #   dataSets[0]["series"][<series_key>]["observations"][<obs_key>] = [value, ...]
    series_map = dataset0.get("series") or {}
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
            value, attr_values = _parse_obs_payload(obs_payload)
            rows.append(
                {**series_values, **obs_values, "OBS_VALUE": value, **attr_values}
            )

    # Layout B — `dimensionAtObservation=AllDimensions` (OECD atual,
    # tambem aceito por UIS SDMX legado): observations diretas no dataSet,
    # com TODAS as dimensoes encodadas no obs_key (series_dims+obs_dims).
    #   dataSets[0]["observations"][<full_key>] = [value, attr_idx_0, ...]
    flat_observations = dataset0.get("observations") or {}
    if flat_observations and not series_map:
        all_dim_ids = series_dim_ids + obs_dim_ids
        all_lookups = series_value_lookups + obs_value_lookups
        for obs_key, obs_payload in flat_observations.items():
            indices = [int(x) for x in str(obs_key).split(":") if x != ""]
            dim_values = {
                all_dim_ids[i]: all_lookups[i][idx]
                if i < len(all_lookups) and idx < len(all_lookups[i])
                else None
                for i, idx in enumerate(indices)
            }
            value, attr_values = _parse_obs_payload(obs_payload)
            rows.append({**dim_values, "OBS_VALUE": value, **attr_values})

    if not rows:
        cols = series_dim_ids + obs_dim_ids + ["OBS_VALUE"] + obs_attr_ids
        return pd.DataFrame(columns=cols or ["TIME_PERIOD", "OBS_VALUE"])

    df = pd.DataFrame(rows)
    if "OBS_VALUE" in df.columns:
        df["OBS_VALUE"] = pd.to_numeric(df["OBS_VALUE"], errors="coerce")
    return df
