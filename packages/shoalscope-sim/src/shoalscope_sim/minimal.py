"""Minimal echosounder simulator for the walking skeleton (roadmap M1.1).

One CW channel, a few stationary on-axis point targets and Gaussian background noise, written
as an EK80 raw file with a ground-truth table. Received power follows the Simrad CW
target-strength equation (Simmonds & MacLennan 2005, ch. 3):

    Pr = TS - 40·log10(R) - 2·α·R + 10·log10(Pt·λ²·G0² / (16·π²))

where R is range, α the absorption coefficient, Pt transmit power, λ wavelength and G0 the
linear on-axis gain. EK80 processing (Kongsberg, and echopype after it) evaluates this equation
at the TVG range R = r - c·τ/4, where r = i·c·Δt/2 is the range of sample i and τ the pulse
duration. Each echo is therefore placed in the single sample whose TVG range is nearest the
target's range, and its power is computed at that sample's TVG range, so a calibrated TS at that
sample returns the inserted value. Beam pattern, pulse shape, motion and the other effects of
the full simulator arrive in M4.

Everything is seeded: the same scenario gives byte-identical files.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from shoalscope_raw.ek80 import Ek80Channel, Ek80Environment, Ek80Ping, write_ek80

if TYPE_CHECKING:
    from pathlib import Path

    from numpy.typing import NDArray

__all__ = [
    "DEFAULT_CHANNEL",
    "MinimalScenario",
    "PointTarget",
    "SimulationResult",
    "received_power_db",
    "sample_ranges_m",
    "simulate",
    "tvg_ranges_m",
]

DEFAULT_CHANNEL = Ek80Channel(
    channel_id="SIM WBT 000001-1 ES38-7_1",
    transceiver_name="SIM WBT 000001",
    transducer_name="ES38-7",
    frequency_hz=38_000.0,
    pulse_duration_s=1.024e-3,
    sample_interval_s=2.56e-4,
    transmit_power_w=1000.0,
    gain_db=26.5,
    sa_correction_db=-0.6,
    equivalent_beam_angle_db=-20.6,
    beamwidth_alongship_deg=7.0,
    beamwidth_athwartship_deg=7.0,
    angle_sensitivity_alongship=21.97,
    angle_sensitivity_athwartship=21.97,
)

TRUTH_SCHEMA = pa.schema(
    [
        pa.field("ping_index", pa.int32(), nullable=False),
        pa.field("ping_time", pa.timestamp("us", tz="UTC"), nullable=False),
        pa.field("channel_id", pa.string(), nullable=False),
        pa.field("target_id", pa.int32(), nullable=False),
        pa.field("sample_index", pa.int32(), nullable=False),
        pa.field("range_m", pa.float64(), nullable=False),
        pa.field("echo_range_m", pa.float64(), nullable=False),
        pa.field("ts_db", pa.float64(), nullable=False),
        pa.field("received_power_db", pa.float64(), nullable=False),
    ]
)


@dataclass(frozen=True)
class PointTarget:
    """A stationary point scatterer on the acoustic axis."""

    range_m: float
    ts_db: float
    first_ping: int = 0
    last_ping: int | None = None  # inclusive; None means until the end


@dataclass(frozen=True)
class MinimalScenario:
    """Everything the minimal simulator needs; serialised into the ground truth."""

    targets: tuple[PointTarget, ...] = (
        PointTarget(range_m=12.0, ts_db=-42.0),
        PointTarget(range_m=25.0, ts_db=-36.0, first_ping=5),
        PointTarget(range_m=33.0, ts_db=-48.0, last_ping=14),
    )
    n_pings: int = 20
    ping_interval_s: float = 1.0
    start: datetime = datetime(2026, 1, 1, tzinfo=UTC)
    max_range_m: float = 40.0
    absorption_db_per_m: float = 0.0098
    noise_power_db: float = -150.0
    noise_sd_db: float = 1.0
    seed: int = 20261102
    channel: Ek80Channel = DEFAULT_CHANNEL
    environment: Ek80Environment = field(default_factory=Ek80Environment)

    def to_json(self) -> str:
        """Stable JSON form used as ground-truth metadata."""
        return json.dumps(asdict(self), default=str, sort_keys=True)


@dataclass(frozen=True)
class SimulationResult:
    """Paths and sizes of what one simulation wrote."""

    raw_path: Path
    truth_path: Path
    raw_bytes: int
    n_echoes: int


def sample_ranges_m(
    channel: Ek80Channel, sound_speed_mps: float, n_samples: int
) -> NDArray[np.float64]:
    """Range of each sample: index · c · Δt / 2."""
    return (
        np.arange(n_samples, dtype=np.float64) * sound_speed_mps * channel.sample_interval_s / 2.0
    )


def tvg_ranges_m(
    channel: Ek80Channel, sound_speed_mps: float, n_samples: int
) -> NDArray[np.float64]:
    """TVG range of each sample for EK80 hardware: r - c·τ/4."""
    offset_m = sound_speed_mps * channel.pulse_duration_s / 4.0
    return sample_ranges_m(channel, sound_speed_mps, n_samples) - offset_m


def received_power_db(
    ts_db: float,
    range_m: float,
    channel: Ek80Channel,
    sound_speed_mps: float,
    absorption_db_per_m: float,
) -> float:
    """Received power of an on-axis point target, from the CW target-strength equation."""
    wavelength_m = sound_speed_mps / channel.frequency_hz
    gain_linear = 10.0 ** (channel.gain_db / 10.0)
    system_db = 10.0 * math.log10(
        channel.transmit_power_w * wavelength_m**2 * gain_linear**2 / (16.0 * math.pi**2)
    )
    spreading_db = 40.0 * math.log10(range_m) + 2.0 * absorption_db_per_m * range_m
    return ts_db - spreading_db + system_db


def simulate(scenario: MinimalScenario, raw_path: Path, truth_path: Path) -> SimulationResult:
    """Write the scenario as an EK80 raw file plus a ground-truth Parquet table."""
    rng = np.random.default_rng(scenario.seed)
    channel, env = scenario.channel, scenario.environment
    c = env.sound_speed_mps
    n_samples = int(scenario.max_range_m / (c * channel.sample_interval_s / 2.0)) + 1
    echo_ranges = sample_ranges_m(channel, c, n_samples)
    tvg_ranges = tvg_ranges_m(channel, c, n_samples)

    pings: list[Ek80Ping] = []
    truth: dict[str, list[object]] = {name: [] for name in TRUTH_SCHEMA.names}
    for index in range(scenario.n_pings):
        time = scenario.start + timedelta(seconds=index * scenario.ping_interval_s)
        noise = rng.normal(scenario.noise_power_db, scenario.noise_sd_db, n_samples)
        power = np.asarray(noise, dtype=np.float64)
        for target_id, target in enumerate(scenario.targets):
            last = scenario.n_pings - 1 if target.last_ping is None else target.last_ping
            if not target.first_ping <= index <= last:
                continue
            sample = int(np.argmin(np.abs(tvg_ranges - target.range_m)))
            sample_range = float(tvg_ranges[sample])
            pr = received_power_db(
                target.ts_db, sample_range, channel, c, scenario.absorption_db_per_m
            )
            power[sample] = pr
            for name, value in (
                ("ping_index", index),
                ("ping_time", time),
                ("channel_id", channel.channel_id),
                ("target_id", target_id),
                ("sample_index", sample),
                ("range_m", sample_range),
                ("echo_range_m", float(echo_ranges[sample])),
                ("ts_db", target.ts_db),
                ("received_power_db", pr),
            ):
                truth[name].append(value)
        pings.append(Ek80Ping(time=time, channel_id=channel.channel_id, power_db=power))

    raw_bytes = write_ek80(raw_path, [channel], env, pings)
    table = pa.table(truth, schema=TRUTH_SCHEMA).replace_schema_metadata(
        {"shoalscope.scenario": scenario.to_json(), "shoalscope.kind": "minimal-v1"}
    )
    pq.write_table(table, truth_path)
    return SimulationResult(raw_path, truth_path, raw_bytes, table.num_rows)
