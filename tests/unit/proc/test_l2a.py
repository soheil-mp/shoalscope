"""L0 to L2A: calibrated Sv from simulated raw files, stored in Icechunk (roadmap M1.2)."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import numpy as np
import pyarrow.parquet as pq
import pytest

from shoalscope_proc.l2a import (
    L2A_GROUP,
    EnvironmentOverride,
    compute_sv,
    open_repository,
    read_window,
    write_window,
)
from shoalscope_raw.ek80 import POWER_DB_PER_COUNT
from shoalscope_sim.minimal import DEFAULT_CHANNEL, MinimalScenario, simulate

if TYPE_CHECKING:
    from pathlib import Path

    import xarray as xr


@pytest.fixture(scope="module")
def window(
    tmp_path_factory: pytest.TempPathFactory,
) -> tuple[MinimalScenario, Path, Path, xr.Dataset]:
    directory = tmp_path_factory.mktemp("l2a")
    scenario = MinimalScenario()
    result = simulate(scenario, directory / "sim.raw", directory / "truth.parquet")
    environment = EnvironmentOverride(
        scenario.environment.sound_speed_mps, scenario.absorption_db_per_m
    )
    return (
        scenario,
        result.raw_path,
        result.truth_path,
        compute_sv(result.raw_path, environment=environment),
    )


def test_sv_of_each_point_target_follows_from_its_ts(
    window: tuple[MinimalScenario, Path, Path, xr.Dataset],
) -> None:
    # For a point target in one sample, Sv - TS = -20 log10(R) - 10 log10(c tau psi / 2) - 2 Sa
    # (Simmonds & MacLennan 2005, ch. 3), with R the TVG range and tau the effective pulse
    # duration echopype derives from the transmit signal.
    scenario, _, truth_path, sv = window
    c = scenario.environment.sound_speed_mps
    tau = float(sv["tau_effective"].values[0])
    psi = 10 ** (DEFAULT_CHANNEL.equivalent_beam_angle_db / 10)
    for row in pq.read_table(truth_path).to_pylist():
        expected = (
            row["ts_db"]
            - 20 * math.log10(row["range_m"])
            - 10 * math.log10(c * tau * psi / 2)
            - 2 * DEFAULT_CHANNEL.sa_correction_db
        )
        cell = sv["Sv"].isel(
            channel=0, ping_time=row["ping_index"], range_sample=row["sample_index"]
        )
        assert float(cell) == pytest.approx(expected, abs=POWER_DB_PER_COUNT)


def test_sv_has_the_window_shape(window: tuple[MinimalScenario, Path, Path, xr.Dataset]) -> None:
    scenario, _, _, sv = window
    assert dict(sv["Sv"].sizes) == {
        "channel": 1,
        "ping_time": scenario.n_pings,
        "range_sample": 209,
    }


def test_file_environment_is_used_without_an_override(
    window: tuple[MinimalScenario, Path, Path, xr.Dataset],
) -> None:
    _, raw, _, with_override = window
    from_file = compute_sv(raw)
    assert float(from_file["sound_speed"]) == pytest.approx(float(with_override["sound_speed"]))
    assert float(from_file["sound_absorption"].values[0]) > 0
    # Samples whose TVG range r - c tau / 4 is negative have no defined Sv; all others do.
    offset_m = float(from_file["sound_speed"]) * DEFAULT_CHANNEL.pulse_duration_s / 4
    defined = from_file["echo_range"].values >= offset_m - 1e-9
    assert np.isfinite(from_file["Sv"].values[defined]).all()
    assert np.isnan(from_file["Sv"].values[~defined]).all()


def test_window_round_trips_through_icechunk(
    window: tuple[MinimalScenario, Path, Path, xr.Dataset], tmp_path: Path
) -> None:
    _, raw, _, sv = window
    repo = open_repository(tmp_path / "repo")
    written = write_window(repo, "sim-0001", raw, sv)
    assert written.group == f"{L2A_GROUP}/sim-0001"
    assert written.n_pings == sv.sizes["ping_time"]
    assert len(written.source_sha256) == 64
    stored = read_window(repo, "sim-0001")
    np.testing.assert_array_equal(stored["Sv"].values, sv["Sv"].values)
    np.testing.assert_array_equal(stored["echo_range"].values, sv["echo_range"].values)
    assert stored.attrs["shoalscope_level"] == "L2A"
    assert stored.attrs["shoalscope_source_sha256"] == written.source_sha256


def test_every_window_is_one_commit_and_history_is_kept(
    window: tuple[MinimalScenario, Path, Path, xr.Dataset], tmp_path: Path
) -> None:
    _, raw, _, sv = window
    repo = open_repository(tmp_path / "repo")
    first = write_window(repo, "a", raw, sv)
    second = write_window(repo, "a", raw, sv.assign(Sv=sv["Sv"] + 1.0))
    assert first.snapshot_id != second.snapshot_id
    messages = [s.message for s in repo.ancestry(branch="main")]
    assert messages[0].startswith("L2A Sv window a from sim.raw")
    old = repo.readonly_session(snapshot_id=first.snapshot_id)
    import xarray as xr  # noqa: PLC0415 - only needed here

    before = xr.open_zarr(old.store, group=f"{L2A_GROUP}/a", consolidated=False)
    np.testing.assert_array_equal(before["Sv"].values, sv["Sv"].values)
    np.testing.assert_array_equal(read_window(repo, "a")["Sv"].values, sv["Sv"].values + 1.0)
    reopened = open_repository(tmp_path / "repo")
    assert read_window(reopened, "a").sizes["ping_time"] == sv.sizes["ping_time"]


@pytest.mark.parametrize("window_id", ["", "../escape", "a/b", "x" * 129])
def test_rejects_unsafe_window_ids(
    window: tuple[MinimalScenario, Path, Path, xr.Dataset], tmp_path: Path, window_id: str
) -> None:
    _, raw, _, sv = window
    with pytest.raises(ValueError, match="window_id"):
        write_window(open_repository(tmp_path / "repo"), window_id, raw, sv)
