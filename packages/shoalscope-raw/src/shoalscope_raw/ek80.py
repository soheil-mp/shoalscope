"""Minimal writer for Simrad EK80 raw files with CW power and angle samples.

An EK80 ``.raw`` file is a sequence of datagrams. Each datagram is framed by its length (a
little-endian int32) before and after it, and starts with a four-character type and a Windows
FILETIME timestamp (100 ns ticks since 1601-01-01 UTC). This module writes the subset a CW
recording needs:

* ``XML0`` *Configuration*: transceivers, channels and transducers with calibration values;
* ``FIL1``: the two decimation-filter stages of each channel (pass-through filters here; they
  matter for complex data, but readers key calibration intervals on them);
* ``XML0`` *Environment*: sound speed, temperature, salinity and depth;
* per ping, ``XML0`` *Parameter*: pulse settings, then ``RAW3``: power and angle samples.

Power is stored as int16 counts of ``10·log10(2)/256`` dB; split-beam angles as two int8 values
per sample (athwartship, alongship), in electrical angle units of 180/128 degrees.

This is the walking-skeleton writer (roadmap M1.1). The complete writer, with ``MRU0`` motion,
``NME0`` positions and index files, is M3.7.
"""

from __future__ import annotations

import math
import struct
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from xml.sax.saxutils import quoteattr

import numpy as np

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

    from numpy.typing import NDArray

__all__ = [
    "POWER_DB_PER_COUNT",
    "Ek80Channel",
    "Ek80Environment",
    "Ek80Ping",
    "datagram",
    "filetime",
    "power_counts",
    "write_ek80",
]

NT_EPOCH = datetime(1601, 1, 1, tzinfo=UTC)
POWER_DB_PER_COUNT = 10.0 * math.log10(2.0) / 256.0
CHANNEL_ID_BYTES = 128
RAW3_POWER_AND_ANGLE = 0b0000_0011


@dataclass(frozen=True)
class Ek80Channel:
    """One CW channel: transceiver, transducer and calibration values as stored in the file."""

    channel_id: str
    transceiver_name: str
    transducer_name: str
    frequency_hz: float
    pulse_duration_s: float
    sample_interval_s: float
    transmit_power_w: float
    gain_db: float
    sa_correction_db: float
    equivalent_beam_angle_db: float
    beamwidth_alongship_deg: float
    beamwidth_athwartship_deg: float
    angle_sensitivity_alongship: float
    angle_sensitivity_athwartship: float
    angle_offset_alongship_deg: float = 0.0
    angle_offset_athwartship_deg: float = 0.0
    impedance_ohm: int = 5400
    rx_sample_frequency_hz: int = 1_500_000


@dataclass(frozen=True)
class Ek80Environment:
    """Water properties recorded in the file's Environment datagram."""

    sound_speed_mps: float = 1500.0
    temperature_c: float = 10.0
    salinity_psu: float = 35.0
    depth_m: float = 100.0
    acidity_ph: float = 8.0
    latitude_deg: float = 45.0


@dataclass(frozen=True)
class Ek80Ping:
    """One ping on one channel: received power in dB re 1 W and optional electrical angles."""

    time: datetime
    channel_id: str
    power_db: NDArray[np.float64]
    angle_athwartship: NDArray[np.int8] | None = None
    angle_alongship: NDArray[np.int8] | None = None


def filetime(when: datetime) -> tuple[int, int]:
    """Low and high 32-bit words of a Windows FILETIME for a timezone-aware datetime."""
    if when.tzinfo is None:
        msg = "timestamps must be timezone-aware"
        raise ValueError(msg)
    ticks = (when - NT_EPOCH) // timedelta(microseconds=1) * 10
    return ticks & 0xFFFF_FFFF, ticks >> 32


def datagram(kind: bytes, when: datetime, body: bytes) -> bytes:
    """Frame one datagram: length, type, timestamp, body, length."""
    if len(kind) != 4:  # noqa: PLR2004 - datagram types are four ASCII characters
        msg = f"datagram type must be 4 bytes, got {kind!r}"
        raise ValueError(msg)
    low, high = filetime(when)
    payload = struct.pack("<4sII", kind, low, high) + body
    length = struct.pack("<i", len(payload))
    return length + payload + length


def power_counts(power_db: NDArray[np.float64]) -> NDArray[np.int16]:
    """Quantise received power in dB to the int16 counts stored in RAW3."""
    counts = np.rint(np.asarray(power_db, dtype=np.float64) / POWER_DB_PER_COUNT)
    info = np.iinfo(np.int16)
    return np.clip(counts, info.min, info.max).astype(np.int16)


def _xml(root: str) -> str:
    return f'<?xml version="1.0" encoding="utf-8"?>\n{root}\n'


def _attrs(values: dict[str, object]) -> str:
    return " ".join(f"{key}={quoteattr(str(value))}" for key, value in values.items())


def _configuration(channels: list[Ek80Channel]) -> str:
    transceivers = []
    for number, ch in enumerate(channels, start=1):
        transducer = _attrs(
            {
                "TransducerName": ch.transducer_name,
                "SerialNumber": 0,
                "Frequency": ch.frequency_hz,
                "FrequencyMinimum": ch.frequency_hz,
                "FrequencyMaximum": ch.frequency_hz,
                "Gain": ch.gain_db,
                "SaCorrection": ch.sa_correction_db,
                "EquivalentBeamAngle": ch.equivalent_beam_angle_db,
                "AngleSensitivityAlongship": ch.angle_sensitivity_alongship,
                "AngleSensitivityAthwartship": ch.angle_sensitivity_athwartship,
                "AngleOffsetAlongship": ch.angle_offset_alongship_deg,
                "AngleOffsetAthwartship": ch.angle_offset_athwartship_deg,
                "BeamWidthAlongship": ch.beamwidth_alongship_deg,
                "BeamWidthAthwartship": ch.beamwidth_athwartship_deg,
                "BeamType": 1,
                "DirectivityDropAt2XBeamWidth": 0,
                "MaxTxPowerTransducer": ch.transmit_power_w,
            }
        )
        channel = _attrs(
            {
                "ChannelID": ch.channel_id,
                "LogicalChannelID": ch.channel_id,
                "ChannelIdShort": ch.transducer_name,
                "MaxTxPowerTransceiver": round(ch.transmit_power_w),
                "PulseDuration": ch.pulse_duration_s,
                "PulseDurationFM": ch.pulse_duration_s,
                "HWChannelConfiguration": 15,
            }
        )
        transceiver = _attrs(
            {
                "TransceiverName": ch.transceiver_name,
                "TransceiverNumber": number,
                "TransceiverType": "WBT",
                "MarketSegment": "Scientific",
                "SerialNumber": number,
                "Impedance": ch.impedance_ohm,
                "Multiplexing": 0,
                "RxSampleFrequency": ch.rx_sample_frequency_hz,
                "TransceiverSoftwareVersion": "shoalscope-sim",
            }
        )
        transceivers.append(
            f"<Transceiver {transceiver}><Channels><Channel {channel}>"
            f"<Transducer {transducer} /></Channel></Channels></Transceiver>"
        )
    header = _attrs(
        {
            "Copyright": "Synthetic data generated by Shoalscope (MIT)",
            "ApplicationName": "EK80",
            "Version": "0.0.0",
            "FileFormatVersion": "1.39",
            "TimeBias": 0,
        }
    )
    return _xml(
        f'<Configuration><Header {header} /><ActivePingMode Mode="Normal" />'
        f'<Transceivers MergeOperation="AddNodeTree">{"".join(transceivers)}</Transceivers>'
        "</Configuration>"
    )


def _environment(env: Ek80Environment) -> str:
    attrs = _attrs(
        {
            "Depth": env.depth_m,
            "Acidity": env.acidity_ph,
            "Salinity": env.salinity_psu,
            "SoundSpeed": env.sound_speed_mps,
            "Temperature": env.temperature_c,
            "Latitude": env.latitude_deg,
            "SoundVelocityProfile": (f"1.0;{env.sound_speed_mps};1000.0;{env.sound_speed_mps}"),
            "SoundVelocitySource": "Manual",
            "DropKeelOffset": 0,
            "DropKeelOffsetIsManual": 0,
            "WaterLevelDraft": 0,
            "WaterLevelDraftIsManual": 0,
            "TowedBodyDepth": 0,
            "TowedBodyDepthIsManual": 0,
        }
    )
    transducer = _attrs({"TransducerName": "Unknown", "SoundSpeed": env.sound_speed_mps})
    return _xml(f"<Environment {attrs}><Transducer {transducer} /></Environment>")


def _parameter(ch: Ek80Channel, env: Ek80Environment) -> str:
    attrs = _attrs(
        {
            "ChannelID": ch.channel_id,
            "ChannelMode": 0,
            "PulseForm": 0,
            "Frequency": ch.frequency_hz,
            "PulseDuration": ch.pulse_duration_s,
            "SampleInterval": ch.sample_interval_s,
            "TransmitPower": ch.transmit_power_w,
            "Slope": 0.5,
            "SoundVelocity": env.sound_speed_mps,
        }
    )
    return _xml(f"<Parameter><Channel {attrs} /></Parameter>")


def _fil1(channel: Ek80Channel, stage: int, decimation_factor: int) -> bytes:
    channel_id = channel.channel_id.encode("utf-8")
    coefficients = np.array([1.0 + 0.0j], dtype="<c8")
    header = struct.pack(
        f"<h2s{CHANNEL_ID_BYTES}shh",
        stage,
        b"\0\0",
        channel_id,
        coefficients.size,
        decimation_factor,
    )
    return header + coefficients.tobytes()


def _raw3(ping: Ek80Ping) -> bytes:
    power = power_counts(ping.power_db)
    count = power.size
    athwart = ping.angle_athwartship
    along = ping.angle_alongship
    angles = np.zeros((count, 2), dtype=np.int8)
    if athwart is not None:
        angles[:, 0] = athwart
    if along is not None:
        angles[:, 1] = along
    channel_id = ping.channel_id.encode("utf-8")
    if len(channel_id) > CHANNEL_ID_BYTES:
        msg = f"channel ID longer than {CHANNEL_ID_BYTES} bytes: {ping.channel_id!r}"
        raise ValueError(msg)
    header = struct.pack(f"<{CHANNEL_ID_BYTES}sHHII", channel_id, RAW3_POWER_AND_ANGLE, 0, 0, count)
    return header + power.astype("<i2").tobytes() + angles.tobytes()


def write_ek80(
    path: Path,
    channels: list[Ek80Channel],
    environment: Ek80Environment,
    pings: Iterable[Ek80Ping],
) -> int:
    """Write a CW EK80 raw file and return its size in bytes.

    Pings must be in time order; each must name one of ``channels``.
    """
    if not channels:
        msg = "at least one channel is required"
        raise ValueError(msg)
    by_id = {ch.channel_id: ch for ch in channels}
    ping_list = list(pings)
    start = ping_list[0].time if ping_list else datetime.now(tz=UTC)
    parts = [datagram(b"XML0", start, _configuration(channels).encode("utf-8"))]
    parts.extend(
        datagram(b"FIL1", start, _fil1(channel, stage, decimation_factor=1))
        for channel in channels
        for stage in (1, 2)
    )
    parts.append(datagram(b"XML0", start, _environment(environment).encode("utf-8")))
    previous = start
    for ping in ping_list:
        if ping.time < previous:
            msg = "pings must be in time order"
            raise ValueError(msg)
        previous = ping.time
        config = by_id.get(ping.channel_id)
        if config is None:
            msg = f"unknown channel {ping.channel_id!r}"
            raise ValueError(msg)
        parts.append(datagram(b"XML0", ping.time, _parameter(config, environment).encode()))
        parts.append(datagram(b"RAW3", ping.time, _raw3(ping)))
    data = b"".join(parts)
    path.write_bytes(data)
    return len(data)
