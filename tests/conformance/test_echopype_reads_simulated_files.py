"""echopype opens simulated EK80 files and recovers the inserted target strengths (M1.1).

echopype is the reference reader and calibrator (ADR-0005). These tests prove that the
simulator writes files a real-world tool reads unchanged, and close the loop from inserted TS
to calibrated TS.
"""

from pathlib import Path

import echopype as ep
import numpy as np
import pyarrow.parquet as pq
import pytest
import xarray as xr

from shoalscope_raw.ek80 import POWER_DB_PER_COUNT
from shoalscope_sim.minimal import DEFAULT_CHANNEL, MinimalScenario, simulate


@pytest.fixture(scope="module")
def simulated(tmp_path_factory: pytest.TempPathFactory) -> tuple[MinimalScenario, Path, Path]:
    directory = tmp_path_factory.mktemp("sim")
    scenario = MinimalScenario()
    result = simulate(scenario, directory / "sim.raw", directory / "truth.parquet")
    return scenario, result.raw_path, result.truth_path


def test_echopype_opens_the_file(simulated: tuple[MinimalScenario, Path, Path]) -> None:
    scenario, raw, _ = simulated
    ed = ep.open_raw(str(raw), sonar_model="EK80")
    beam = ed["Sonar/Beam_group1"]
    assert beam.sizes["channel"] == 1
    assert beam.sizes["ping_time"] == scenario.n_pings
    assert str(beam["channel"].values[0]) == DEFAULT_CHANNEL.channel_id
    assert float(beam["frequency_nominal"].values[0]) == DEFAULT_CHANNEL.frequency_hz


def test_power_is_read_back_within_quantisation(
    simulated: tuple[MinimalScenario, Path, Path],
) -> None:
    _, raw, truth_path = simulated
    power = ep.open_raw(str(raw), sonar_model="EK80")["Sonar/Beam_group1"]["backscatter_r"]
    for row in pq.read_table(truth_path).to_pylist():
        read = float(
            power.isel(channel=0, ping_time=row["ping_index"], range_sample=row["sample_index"])
        )
        assert read == pytest.approx(row["received_power_db"], abs=POWER_DB_PER_COUNT / 2)


def test_calibrated_ts_returns_the_inserted_ts(
    simulated: tuple[MinimalScenario, Path, Path],
) -> None:
    scenario, raw, truth_path = simulated
    ed = ep.open_raw(str(raw), sonar_model="EK80")
    channels = ed["Sonar/Beam_group1"]["channel"].values
    env = {
        "sound_speed": scenario.environment.sound_speed_mps,
        "sound_absorption": xr.DataArray(
            [scenario.absorption_db_per_m], dims=["channel"], coords={"channel": channels}
        ),
    }
    ts = ep.calibrate.compute_TS(ed, waveform_mode="CW", encode_mode="power", env_params=env)
    truth = pq.read_table(truth_path).to_pylist()
    errors = np.array(
        [
            float(
                ts["TS"].isel(channel=0, ping_time=r["ping_index"], range_sample=r["sample_index"])
            )
            - r["ts_db"]
            for r in truth
        ]
    )
    assert np.abs(errors).max() <= POWER_DB_PER_COUNT
    echo_range = ts["echo_range"].isel(channel=0, ping_time=0).values
    np.testing.assert_allclose(
        [echo_range[r["sample_index"]] for r in truth], [r["echo_range_m"] for r in truth]
    )
