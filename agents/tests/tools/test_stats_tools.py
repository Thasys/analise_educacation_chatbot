"""Sprint 5.3 — testes de stats_tools (helpers + ComputeStatsTool)."""

from __future__ import annotations

import json
import math

import pytest

from src.tools import compute_position, compute_summary_stats
from src.tools.stats_tools import ComputeStatsTool


# ----------------------------------------------------------------------
# compute_summary_stats (helper puro)
# ----------------------------------------------------------------------


def test_summary_stats_typical_set():
    values = [4.50, 5.62, 5.77, 6.05, 6.68]
    s = compute_summary_stats(values)
    assert s["sample_size"] == 5
    assert s["min"] == 4.50
    assert s["max"] == 6.68
    assert s["mean"] == pytest.approx(5.724, rel=1e-3)
    assert s["median"] == 5.77
    assert s["stddev"] == pytest.approx(0.796, abs=1e-3)
    # CV razoavelmente baixo (~0.14) para indicador macroeconomico.
    assert 0.10 < s["cv"] < 0.20


def test_summary_stats_empty_returns_zeros():
    s = compute_summary_stats([])
    assert s["sample_size"] == 0
    assert s["mean"] == 0.0
    assert s["stddev"] == 0.0


def test_summary_stats_single_value_no_stddev():
    s = compute_summary_stats([5.0])
    assert s["sample_size"] == 1
    assert s["stddev"] == 0.0
    assert s["cv"] == 0.0


# ----------------------------------------------------------------------
# compute_position
# ----------------------------------------------------------------------


def test_position_brazil_above_oecd_mean_in_spending():
    # BR=6.09 (gasto BR 2018), OECD-like distribution com media 5.04.
    universe = [3.5, 4.50, 5.04, 5.62, 6.09, 6.68]
    pos = compute_position(6.09, universe, higher_is_better=True)
    assert pos["zscore"] > 0  # acima da media
    assert 0.0 < pos["percentile"] <= 1.0
    # rank: ha 1 valor > 6.09 (6.68) -> rank=2
    assert pos["rank"] == 2
    assert pos["gap_to_mean"] == pytest.approx(6.09 - sum(universe) / len(universe))


def test_position_below_mean():
    universe = [10.0, 20.0, 30.0, 40.0, 50.0]
    pos = compute_position(15.0, universe, higher_is_better=True)
    assert pos["zscore"] < 0
    assert pos["gap_to_mean"] == -15.0


def test_position_lower_is_better_inverts_percentile():
    # Taxa de analfabetismo: baixo eh bom
    universe = [1.0, 5.0, 10.0, 20.0, 30.0]
    pos_low = compute_position(2.0, universe, higher_is_better=False)
    pos_high = compute_position(25.0, universe, higher_is_better=False)
    assert pos_low["percentile"] > pos_high["percentile"]


def test_position_empty_universe_safe():
    pos = compute_position(5.0, [])
    assert pos["zscore"] == 0.0
    assert pos["rank"] == 0


# ----------------------------------------------------------------------
# ComputeStatsTool
# ----------------------------------------------------------------------


def test_compute_stats_tool_summary_only():
    tool = ComputeStatsTool()
    raw = tool.run(values=[4.50, 5.62, 6.05, 6.68])
    payload = json.loads(raw)
    assert payload["ok"] is True
    assert payload["summary"]["sample_size"] == 4
    assert "focus_position" not in payload


def test_compute_stats_tool_with_focus():
    tool = ComputeStatsTool()
    raw = tool.run(
        values=[4.50, 5.62, 6.05, 6.68],
        focus_value=5.62,
    )
    payload = json.loads(raw)
    assert payload["ok"] is True
    assert "focus_position" in payload
    assert payload["focus_position"]["rank"] >= 1


def test_compute_stats_tool_validation_error_empty_list():
    tool = ComputeStatsTool()
    raw = tool.run(values=[])
    payload = json.loads(raw)
    assert payload["ok"] is False
    assert payload["error"]["error_type"] == "validation"


def test_compute_stats_tool_higher_is_better_false():
    tool = ComputeStatsTool()
    raw = tool.run(
        values=[1.0, 5.0, 10.0, 20.0, 30.0],
        focus_value=2.0,
        higher_is_better=False,
    )
    payload = json.loads(raw)
    assert payload["focus_position"]["rank"] == 2  # 1.0 e melhor (mais baixo)
