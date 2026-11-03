"""L3 MVBS and L4 NASC per time cell (roadmap M1.3)."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import numpy as np
import pyarrow.parquet as pq
import pytest
import xarray as xr

from shoalscope_proc.integration import NASC_PER_SA, mvbs, nasc_time_cells
from shoalscope_proc.l2a import EnvironmentOverride, compute_sv
from shoalscope_sim.minimal import DEFAULT_CHANNEL, MinimalScenario, simulate

if TYPE_CHECKING:
    from pathlib import Path

DR = 0.192


def constant_sv(sv_db: np.ndarray, *, n_samples: int = 200, interval_s: float = 1.0) -> xr.Dataset:
    """An Sv dataset with one channel; ``sv_db`` holds one value per ping."""
    n_pings = len(sv_db)
    times = np.datetime64("2026-01-01T00:00:00", "ns") + (
        np.arange(n_pings) * interval_s * 1e9
    ).astype("timedelta64[ns]")
    ranges = np.broadcast_to(np.arange(n_samples) * DR, (1, n_pings, n_samples))
    values = np.broadcast_to(np.asarray(sv_db, dtype=float)[None, :, None], (1, n_pings, n_samples))
    dims = ("channel", "ping_time", "range_sample")
    return xr.Dataset(
        {
            "Sv": (dims, values.copy()),
            "echo_range": (dims, ranges.copy()),
            "frequency_nominal": (("channel",), [38_000.0]),
        },
        coords={"channel": ["ch1"], "ping_time": times, "range_sample": np.arange(n_samples)},
    )


class TestNasc:
    def test_uniform_layer(self) -> None:
        # sv = 1e-7 m-1 over the ten samples 10..19: sa = 1e-7 * 10 * dr.
        sv = constant_sv(np.full(4, -70.0))
        cells = nasc_time_cells(
            sv, cell_s=60, range_min_m=10 * DR - 1e-9, range_max_m=20 * DR - 1e-9
        )
        expected = NASC_PER_SA * 1e-7 * 10 * DR
        assert float(cells["nasc_m2_per_nmi2"].values[0, 0]) == pytest.approx(expected)
        assert float(NASC_PER_SA * 1e-6) == pytest.approx(43.1, abs=0.05)

    def test_averages_pings_in_the_linear_domain(self) -> None:
        sv = constant_sv(np.array([-60.0, -70.0]))
        cells = nasc_time_cells(sv, cell_s=60)
        expected = NASC_PER_SA * (1e-6 + 1e-7) / 2 * 200 * DR
        assert float(cells["nasc_m2_per_nmi2"].values[0, 0]) == pytest.approx(expected)
        decibel_mean = NASC_PER_SA * 10 ** (-6.5) * 200 * DR
        assert float(cells["nasc_m2_per_nmi2"].values[0, 0]) > 1.5 * decibel_mean

    def test_cells_are_aligned_to_the_epoch(self) -> None:
        sv = constant_sv(np.full(25, -60.0))
        cells = nasc_time_cells(sv, cell_s=10)
        assert cells.sizes["cell_start"] == 3
        assert cells["n_pings"].values.tolist() == [10, 10, 5]
        assert str(cells["cell_start"].values[1]) == "2026-01-01T00:00:10.000000000"

    def test_skips_undefined_samples(self) -> None:
        sv = constant_sv(np.full(2, -60.0))
        sv["Sv"].values[..., :50] = np.nan
        cells = nasc_time_cells(sv)
        assert float(cells["nasc_m2_per_nmi2"].values[0, 0]) == pytest.approx(
            NASC_PER_SA * 1e-6 * 150 * DR
        )

    @pytest.mark.parametrize(("kwargs"), [{"cell_s": 0}, {"range_min_m": 5.0, "range_max_m": 5.0}])
    def test_rejects_bad_parameters(self, kwargs: dict[str, float]) -> None:
        with pytest.raises(ValueError, match="positive"):
            nasc_time_cells(constant_sv(np.zeros(2)), **kwargs)

    def test_rejects_uneven_range_samples(self) -> None:
        sv = constant_sv(np.zeros(2), n_samples=4)
        sv["echo_range"].values[..., 3] = 99.0
        with pytest.raises(ValueError, match="evenly spaced"):
            nasc_time_cells(sv)


class TestMvbs:
    def test_mvbs_averages_in_the_linear_domain(self) -> None:
        sv = constant_sv(np.array([-60.0, -70.0]), n_samples=20)
        result = mvbs(sv, range_bin_m=1.0, ping_time_bin_s=10.0)
        value = float(result["Sv"].isel(channel=0, ping_time=0, echo_range=0))
        assert value == pytest.approx(10 * math.log10((1e-6 + 1e-7) / 2))

    def test_rejects_non_positive_bins(self) -> None:
        with pytest.raises(ValueError, match="positive"):
            mvbs(constant_sv(np.zeros(2)), range_bin_m=0)


def test_nasc_of_simulated_targets_matches_ground_truth(tmp_path: Path) -> None:
    # With negligible noise, each cell's NASC is the mean over its pings of the targets' sv * dr.
    scenario = MinimalScenario(noise_power_db=-300.0, noise_sd_db=0.0)
    result = simulate(scenario, tmp_path / "sim.raw", tmp_path / "truth.parquet")
    environment = EnvironmentOverride(
        scenario.environment.sound_speed_mps, scenario.absorption_db_per_m
    )
    sv = compute_sv(result.raw_path, environment=environment)
    cells = nasc_time_cells(sv, cell_s=10.0, range_min_m=1.0)

    c = scenario.environment.sound_speed_mps
    tau = float(sv["tau_effective"].values[0])
    psi = 10 ** (DEFAULT_CHANNEL.equivalent_beam_angle_db / 10)
    dr = c * DEFAULT_CHANNEL.sample_interval_s / 2
    sa = np.zeros(2)
    for row in pq.read_table(result.truth_path).to_pylist():
        sv_db = row["ts_db"] - 20 * math.log10(row["range_m"]) - 10 * math.log10(c * tau * psi / 2)
        sv_db -= 2 * DEFAULT_CHANNEL.sa_correction_db
        sa[row["ping_index"] // 10] += 10 ** (sv_db / 10) * dr / 10
    np.testing.assert_allclose(cells["nasc_m2_per_nmi2"].values[0], NASC_PER_SA * sa, rtol=0.01)
    assert cells.attrs["sample_thickness_m"] == pytest.approx(dr)
