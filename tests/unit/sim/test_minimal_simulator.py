"""Tests for the minimal simulator (M1.1)."""

import json
import math
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np
import pyarrow.parquet as pq
import pytest

from shoalscope_sim.minimal import (
    DEFAULT_CHANNEL,
    MinimalScenario,
    PointTarget,
    received_power_db,
    sample_ranges_m,
    simulate,
    tvg_ranges_m,
)


def run(
    tmp_path: Path, scenario: MinimalScenario, name: str = "a"
) -> tuple[bytes, list[dict[str, Any]]]:
    result = simulate(scenario, tmp_path / f"{name}.raw", tmp_path / f"{name}.parquet")
    return result.raw_path.read_bytes(), pq.read_table(result.truth_path).to_pylist()


def test_same_seed_gives_identical_files(tmp_path: Path) -> None:
    raw_a, truth_a = run(tmp_path, MinimalScenario(), "a")
    raw_b, truth_b = run(tmp_path, MinimalScenario(), "b")
    assert raw_a == raw_b
    assert truth_a == truth_b


def test_another_seed_changes_only_the_noise(tmp_path: Path) -> None:
    raw_a, truth_a = run(tmp_path, MinimalScenario(), "a")
    raw_b, truth_b = run(tmp_path, MinimalScenario(seed=7), "b")
    assert raw_a != raw_b
    assert truth_a == truth_b


def test_truth_respects_target_ping_windows(tmp_path: Path) -> None:
    scenario = MinimalScenario()
    _, truth = run(tmp_path, scenario)
    per_target = {i: [r["ping_index"] for r in truth if r["target_id"] == i] for i in range(3)}
    assert per_target[0] == list(range(20))
    assert per_target[1] == list(range(5, 20))
    assert per_target[2] == list(range(15))


def test_echoes_land_at_the_nearest_tvg_range(tmp_path: Path) -> None:
    scenario = MinimalScenario()
    _, truth = run(tmp_path, scenario)
    spacing = scenario.environment.sound_speed_mps * DEFAULT_CHANNEL.sample_interval_s / 2
    by_target = {r["target_id"]: r for r in truth}
    for target_id, target in enumerate(scenario.targets):
        row = by_target[target_id]
        assert abs(row["range_m"] - target.range_m) <= spacing / 2
        offset = scenario.environment.sound_speed_mps * DEFAULT_CHANNEL.pulse_duration_s / 4
        assert row["echo_range_m"] == pytest.approx(row["range_m"] + offset)


def test_truth_carries_the_scenario(tmp_path: Path) -> None:
    result = simulate(MinimalScenario(), tmp_path / "a.raw", tmp_path / "a.parquet")
    meta = pq.read_schema(result.truth_path).metadata
    scenario = json.loads(meta[b"shoalscope.scenario"])
    assert scenario["seed"] == MinimalScenario().seed
    assert meta[b"shoalscope.kind"] == b"minimal-v1"
    assert result.n_echoes == 50


def test_target_outside_the_range_window_is_clamped_to_the_last_sample(tmp_path: Path) -> None:
    scenario = MinimalScenario(targets=(PointTarget(range_m=1000.0, ts_db=-40.0),), n_pings=2)
    _, truth = run(tmp_path, scenario)
    assert {r["sample_index"] for r in truth} == {208}


def test_ranges() -> None:
    ranges = sample_ranges_m(DEFAULT_CHANNEL, 1500.0, 3)
    np.testing.assert_allclose(ranges, [0.0, 0.192, 0.384])
    np.testing.assert_allclose(tvg_ranges_m(DEFAULT_CHANNEL, 1500.0, 3), ranges - 0.384)


def test_received_power_matches_a_hand_calculation() -> None:
    wavelength = 1500.0 / 38_000.0
    gain = 10 ** (26.5 / 10)
    system = 10 * math.log10(1000.0 * wavelength**2 * gain**2 / (16 * math.pi**2))
    expected = -40.0 - 40 * math.log10(20.0) - 2 * 0.0098 * 20.0 + system
    got = received_power_db(-40.0, 20.0, DEFAULT_CHANNEL, 1500.0, 0.0098)
    assert got == pytest.approx(expected)


def test_received_power_falls_with_range() -> None:
    powers = [received_power_db(-40.0, r, DEFAULT_CHANNEL, 1500.0, 0.01) for r in (5, 10, 20)]
    assert powers == sorted(powers, reverse=True)


def test_scenario_json_is_stable() -> None:
    assert MinimalScenario().to_json() == replace(MinimalScenario()).to_json()
