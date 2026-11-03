"""Minimal L0 to L2A: raw EK80 file to calibrated volume backscattering strength (roadmap M1.2).

The walking skeleton reads a raw file with echopype (the reference reader and calibrator,
ADR-0005), computes Sv for CW power data with the calibration values stored in the file (gain,
Sa correction, equivalent beam angle), and writes the window to an Icechunk repository as one
commit (ADR-0006). Every commit names the source file and its SHA-256, so each array in the
store can be traced back to the bytes it came from.

Layout inside the repository: one Zarr group per window, ``l2a/sv/<window_id>``, holding the
echopype ``Sv`` dataset (``Sv`` and ``echo_range`` by channel, ping time and range sample).
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

import echopype as ep
import icechunk
import icechunk.xarray
import xarray as xr

if TYPE_CHECKING:
    from pathlib import Path

__all__ = [
    "L2A_GROUP",
    "EnvironmentOverride",
    "WindowWrite",
    "compute_sv",
    "open_repository",
    "read_window",
    "write_window",
]

L2A_GROUP: Final = "l2a/sv"
"""Parent group of every L2A window in the repository."""

_WINDOW_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
_CHUNK_BYTES: Final = 1 << 20


@dataclass(frozen=True, slots=True)
class EnvironmentOverride:
    """Sound speed and absorption to use instead of the values derived from the file.

    Attributes:
        sound_speed_mps: Speed of sound in water.
        absorption_db_per_m: Absorption coefficient, one value for every channel.
    """

    sound_speed_mps: float
    absorption_db_per_m: float


@dataclass(frozen=True, slots=True)
class WindowWrite:
    """What :func:`write_window` committed."""

    window_id: str
    group: str
    snapshot_id: str
    source_sha256: str
    n_pings: int


def compute_sv(raw_path: Path, *, environment: EnvironmentOverride | None = None) -> xr.Dataset:
    """Open an EK80 raw file and compute CW Sv with the file's calibration values.

    Args:
        raw_path: The raw file.
        environment: Sound speed and absorption to use; when ``None``, echopype derives them from
            the environment datagram in the file.

    Returns:
        echopype's Sv dataset, with dimensions ``channel``, ``ping_time`` and ``range_sample``.
    """
    echodata = ep.open_raw(str(raw_path), sonar_model="EK80")
    env_params = None
    if environment is not None:
        channels = echodata["Sonar/Beam_group1"]["channel"].values
        env_params = {
            "sound_speed": environment.sound_speed_mps,
            # echopype needs one absorption value per channel, as a DataArray.
            "sound_absorption": xr.DataArray(
                [environment.absorption_db_per_m] * len(channels),
                dims=["channel"],
                coords={"channel": channels},
            ),
        }
    sv: xr.Dataset = ep.calibrate.compute_Sv(
        echodata, waveform_mode="CW", encode_mode="power", env_params=env_params
    )
    return sv


def open_repository(path: Path) -> icechunk.Repository:
    """Open the Icechunk repository at ``path`` on local disk, creating it if needed."""
    return icechunk.Repository.open_or_create(icechunk.local_filesystem_storage(str(path)))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _chunked(sv: xr.Dataset) -> xr.Dataset:
    """Chunk along ping time so that one chunk of Sv holds about 1 MiB."""
    per_ping = max(1, sv["Sv"].isel(ping_time=0).size * sv["Sv"].dtype.itemsize)
    pings = max(1, min(sv.sizes["ping_time"], _CHUNK_BYTES // per_ping))
    return sv.chunk({"ping_time": pings})


def write_window(
    repo: icechunk.Repository,
    window_id: str,
    raw_path: Path,
    sv: xr.Dataset,
    *,
    branch: str = "main",
) -> WindowWrite:
    """Write one window of Sv to its own group and commit it.

    Writing the same window again replaces its group in a new commit; earlier commits keep the
    old version.

    Raises:
        ValueError: If the window id is not a safe group name.
    """
    if not _WINDOW_ID.match(window_id):
        msg = f"window_id must be 1-128 letters, digits, '.', '_' or '-', got {window_id!r}"
        raise ValueError(msg)
    group = f"{L2A_GROUP}/{window_id}"
    source = _sha256(raw_path)
    dataset = sv[["Sv", "echo_range"]].assign_attrs(
        {
            "shoalscope_level": "L2A",
            "shoalscope_window_id": window_id,
            "shoalscope_source_file": raw_path.name,
            "shoalscope_source_sha256": source,
            "shoalscope_calibration": "echopype compute_Sv, CW, power, file calibration values",
        }
    )
    session = repo.writable_session(branch)
    icechunk.xarray.to_icechunk(_chunked(dataset), session, group=group, mode="w")
    snapshot = session.commit(f"L2A Sv window {window_id} from {raw_path.name} ({source[:12]})")
    return WindowWrite(window_id, group, snapshot, source, int(sv.sizes["ping_time"]))


def read_window(repo: icechunk.Repository, window_id: str, *, branch: str = "main") -> xr.Dataset:
    """Open one L2A window for reading (lazily, from the branch head)."""
    session = repo.readonly_session(branch=branch)
    stored: xr.Dataset = xr.open_zarr(
        session.store, group=f"{L2A_GROUP}/{window_id}", consolidated=False
    )
    return stored
