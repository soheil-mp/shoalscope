"""Tests for the minimal EK80 writer (M1.1)."""

import struct
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st

from shoalscope_raw.ek80 import (
    NT_EPOCH,
    POWER_DB_PER_COUNT,
    Ek80Environment,
    Ek80Ping,
    datagram,
    filetime,
    power_counts,
    write_ek80,
)
from shoalscope_sim.minimal import DEFAULT_CHANNEL


def walk(data: bytes) -> list[tuple[str, int]]:
    """Frame-walk a raw file: (type, body length) per datagram, checking both length fields."""
    out, pos = [], 0
    while pos < len(data):
        (length,) = struct.unpack_from("<i", data, pos)
        (trailer,) = struct.unpack_from("<i", data, pos + 4 + length)
        assert trailer == length
        out.append((data[pos + 4 : pos + 8].decode(), length - 12))
        pos += 4 + length + 4
    assert pos == len(data)
    return out


# Hypothesis takes naive bounds and draws naive datetimes; UTC is attached in the test.
@given(st.datetimes(min_value=datetime(1970, 1, 1), max_value=datetime(2100, 1, 1)))  # noqa: DTZ001
def test_filetime_round_trips_to_the_microsecond(naive: datetime) -> None:
    when = naive.replace(tzinfo=UTC)
    low, high = filetime(when)
    ticks = (high << 32) | low
    assert NT_EPOCH + timedelta(microseconds=ticks // 10) == when


def test_filetime_rejects_naive_datetimes() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        filetime(datetime(2026, 1, 1))  # noqa: DTZ001 - the point of the test


def test_datagram_is_framed_by_its_length() -> None:
    raw = datagram(b"XML0", datetime(2026, 1, 1, tzinfo=UTC), b"<a/>")
    assert walk(raw) == [("XML0", 4)]


def test_datagram_type_must_be_four_bytes() -> None:
    with pytest.raises(ValueError, match="4 bytes"):
        datagram(b"RAW", datetime(2026, 1, 1, tzinfo=UTC), b"")


@given(st.floats(min_value=-380.0, max_value=380.0))
def test_power_quantisation_error_is_at_most_half_a_count(power_db: float) -> None:
    counts = power_counts(np.array([power_db]))
    assert abs(float(counts[0]) * POWER_DB_PER_COUNT - power_db) <= POWER_DB_PER_COUNT / 2


def test_power_is_clipped_to_int16() -> None:
    counts = power_counts(np.array([-1e6, 1e6]))
    assert counts.tolist() == [-32768, 32767]


def _ping(index: int, n: int = 8, channel_id: str = DEFAULT_CHANNEL.channel_id) -> Ek80Ping:
    time = datetime(2026, 1, 1, tzinfo=UTC) + timedelta(seconds=index)
    return Ek80Ping(time=time, channel_id=channel_id, power_db=np.full(n, -100.0))


def test_file_layout(tmp_path: Path) -> None:
    path = tmp_path / "x.raw"
    size = write_ek80(path, [DEFAULT_CHANNEL], Ek80Environment(), [_ping(0), _ping(1)])
    data = path.read_bytes()
    assert size == len(data)
    kinds = [kind for kind, _ in walk(data)]
    assert kinds == ["XML0", "FIL1", "FIL1", "XML0", "XML0", "RAW3", "XML0", "RAW3"]


def test_raw3_holds_power_then_angles(tmp_path: Path) -> None:
    path = tmp_path / "x.raw"
    along = np.arange(8, dtype=np.int8)
    athwart = -along
    ping = Ek80Ping(
        time=datetime(2026, 1, 1, tzinfo=UTC),
        channel_id=DEFAULT_CHANNEL.channel_id,
        power_db=np.linspace(-120.0, -60.0, 8),
        angle_athwartship=athwart,
        angle_alongship=along,
    )
    write_ek80(path, [DEFAULT_CHANNEL], Ek80Environment(), [ping])
    data = path.read_bytes()
    raw3 = data.rindex(b"RAW3")
    body = data[raw3 + 12 :]
    datatype, _, offset, count = struct.unpack_from("<HHII", body, 128)
    assert (datatype, offset, count) == (0b11, 0, 8)
    power = np.frombuffer(body, dtype="<i2", count=8, offset=140)
    angles = np.frombuffer(body, dtype=np.int8, count=16, offset=156).reshape(8, 2)
    np.testing.assert_array_equal(power, power_counts(ping.power_db))
    np.testing.assert_array_equal(angles[:, 1], along)
    np.testing.assert_array_equal(angles[:, 0], athwart)


@pytest.mark.parametrize(
    ("pings", "message"),
    [
        ([_ping(1), _ping(0)], "time order"),
        ([_ping(0, channel_id="nope")], "unknown channel"),
    ],
)
def test_invalid_pings_are_rejected(tmp_path: Path, pings: list[Ek80Ping], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        write_ek80(tmp_path / "x.raw", [DEFAULT_CHANNEL], Ek80Environment(), pings)


def test_channel_ids_longer_than_the_field_are_rejected(tmp_path: Path) -> None:
    long_channel = replace(DEFAULT_CHANNEL, channel_id="x" * 129)
    ping = _ping(0, channel_id=long_channel.channel_id)
    with pytest.raises(ValueError, match="longer than 128 bytes"):
        write_ek80(tmp_path / "x.raw", [long_channel], Ek80Environment(), [ping])


def test_at_least_one_channel_is_required(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="at least one channel"):
        write_ek80(tmp_path / "x.raw", [], Ek80Environment(), [])
