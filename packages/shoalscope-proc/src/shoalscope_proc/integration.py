"""Minimal L3 and L4: mean volume backscattering strength and echo integration (roadmap M1.3).

* **L3, MVBS**: Sv averaged on a fixed range by ping-time grid with
  :func:`echopype.commongrid.compute_MVBS`, which averages in the linear domain.
* **L4, NASC per time cell**: the nautical area scattering coefficient of every channel and
  time cell. echopype's ``compute_NASC`` bins by sailed distance and needs a ship's track; a
  moored or bottom-mounted echosounder does not move, so Shoalscope integrates per time cell.

Echo integration follows the definitions of MacLennan, Fernandes & Dalen (2002):

.. code-block:: text

    sv    = 10^(Sv / 10)                       volume backscattering coefficient, m-1
    sa    = sum over samples of sv * dr        area backscattering coefficient, m2 m-2
    NASC  = 4 * pi * 1852^2 * sa               m2 nmi-2

``dr`` is the sample thickness ``c * dt / 2``. Within a time cell, ``sa`` is the mean over its
pings in the linear domain, never in decibels. Samples outside ``[range_min_m, range_max_m)`` and
samples without a defined Sv (inside the near field of the TVG) are left out.

Reference: MacLennan, D. N., Fernandes, P. G. & Dalen, J. (2002). A consistent approach to
definitions and symbols in fisheries acoustics. *ICES Journal of Marine Science*, 59(2),
365-369.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime, timedelta
from typing import Final

import echopype as ep
import numpy as np
import xarray as xr

from shoalscope_core.levels import Level, ProcessingAttributes, configuration_hash
from shoalscope_core.tables import NASC_CELLS
from shoalscope_core.units import Decibels

__all__ = ["NASC_PER_SA", "l4_attributes", "mvbs", "nasc_rows", "nasc_time_cells"]

NASC_PER_SA: Final = 4.0 * math.pi * 1852.0**2
"""Factor from the area backscattering coefficient sa (m2 m-2) to NASC (m2 nmi-2)."""


def mvbs(sv: xr.Dataset, *, range_bin_m: float = 1.0, ping_time_bin_s: float = 10.0) -> xr.Dataset:
    """Mean volume backscattering strength on a fixed grid (L3).

    Args:
        sv: echopype Sv dataset.
        range_bin_m: Height of a range bin.
        ping_time_bin_s: Length of a ping-time bin.

    Returns:
        echopype's MVBS dataset, with ``Sv`` averaged in the linear domain and dimensions
        ``channel``, ``ping_time`` (bin starts) and ``echo_range`` (bin starts).
    """
    if range_bin_m <= 0 or ping_time_bin_s <= 0:
        msg = "range_bin_m and ping_time_bin_s must be positive"
        raise ValueError(msg)
    result: xr.Dataset = ep.commongrid.compute_MVBS(
        sv,
        range_var="echo_range",
        range_bin=f"{range_bin_m}m",
        ping_time_bin=f"{ping_time_bin_s}s",
    )
    return result


def nasc_time_cells(
    sv: xr.Dataset,
    *,
    cell_s: float = 60.0,
    range_min_m: float = 0.0,
    range_max_m: float = math.inf,
) -> xr.Dataset:
    """NASC of every channel and time cell (L4).

    Time cells are aligned to multiples of ``cell_s`` since the Unix epoch, so cells from
    neighbouring windows line up.

    Args:
        sv: echopype Sv dataset with ``Sv`` and ``echo_range`` by channel, ping time and range
            sample.
        cell_s: Length of a time cell.
        range_min_m: Lower integration limit (inclusive).
        range_max_m: Upper integration limit (exclusive).

    Returns:
        A dataset with ``nasc_m2_per_nmi2`` and ``n_pings`` by ``channel`` and ``cell_start``.

    Raises:
        ValueError: If the limits are inverted, the cell length is not positive or the range
            samples are not evenly spaced.
    """
    if cell_s <= 0 or not range_min_m < range_max_m:
        msg = "cell_s must be positive and range_min_m < range_max_m"
        raise ValueError(msg)
    echo_range = sv["echo_range"].transpose("channel", "ping_time", "range_sample").values
    sv_db = sv["Sv"].transpose("channel", "ping_time", "range_sample").values
    steps = np.diff(echo_range, axis=-1)
    dr = float(np.nanmedian(steps))
    if not np.allclose(steps[np.isfinite(steps)], dr, rtol=1e-6):
        msg = "range samples must be evenly spaced"
        raise ValueError(msg)

    inside = (echo_range >= range_min_m) & (echo_range < range_max_m) & np.isfinite(sv_db)
    sv_linear = Decibels(np.where(inside, sv_db, -np.inf)).to_linear().value  # 0 outside
    sa_per_ping = sv_linear.sum(axis=-1) * dr  # (channel, ping)

    cell_ns = round(cell_s * 1e9)
    times_ns = sv["ping_time"].values.astype("datetime64[ns]").astype(np.int64)
    cell_numbers, index = np.unique(times_ns // cell_ns, return_inverse=True)
    starts = (cell_numbers * cell_ns).astype("datetime64[ns]")
    n_channels = sa_per_ping.shape[0]
    sums = np.zeros((n_channels, len(starts)))
    counts = np.zeros(len(starts), dtype=np.int64)
    np.add.at(sums.T, index, sa_per_ping.T)
    np.add.at(counts, index, 1)
    nasc = NASC_PER_SA * sums / counts
    return xr.Dataset(
        {
            "nasc_m2_per_nmi2": (("channel", "cell_start"), nasc),
            "n_pings": (("cell_start",), counts),
        },
        coords={"channel": sv["channel"].values, "cell_start": starts},
        attrs={
            "cell_s": cell_s,
            "range_min_m": range_min_m,
            "range_max_m": range_max_m
            if math.isfinite(range_max_m)
            else float(np.nanmax(echo_range)),
            "sample_thickness_m": dr,
            "method": "per-ping sa = sum(sv * dr), linear mean over pings, NASC = 4 pi 1852^2 sa",
        },
    )


def nasc_rows(
    cells: xr.Dataset, *, window_id: str, source_sha256: str, frequency_hz: dict[str, float]
) -> list[dict[str, object]]:
    """Rows of the ``l4.nasc_cells`` contract (:data:`shoalscope_core.tables.NASC_CELLS`).

    Args:
        cells: Output of :func:`nasc_time_cells`.
        window_id: Window the cells came from.
        source_sha256: SHA-256 of the raw file.
        frequency_hz: Nominal frequency of each channel.
    """
    width = timedelta(seconds=float(cells.attrs["cell_s"]))
    rows: list[dict[str, object]] = []
    for c, channel in enumerate(cells["channel"].values.tolist()):
        for k, start_ns in enumerate(
            cells["cell_start"].values.astype("datetime64[ns]").astype(np.int64)
        ):
            start = datetime.fromtimestamp(0, tz=UTC) + timedelta(
                microseconds=int(start_ns) // 1_000
            )
            rows.append(
                {
                    "window_id": window_id,
                    "channel_id": str(channel),
                    "frequency_hz": float(frequency_hz[str(channel)]),
                    "cell_start": start,
                    "cell_end": start + width,
                    "range_min_m": float(cells.attrs["range_min_m"]),
                    "range_max_m": float(cells.attrs["range_max_m"]),
                    "nasc_m2_per_nmi2": float(cells["nasc_m2_per_nmi2"].values[c, k]),
                    "n_pings": int(cells["n_pings"].values[k]),
                    "source_sha256": source_sha256,
                }
            )
    assert all(tuple(r) == NASC_CELLS.names for r in rows)  # noqa: S101 - contract invariant
    return rows


def l4_attributes(cells: xr.Dataset, sv_attributes: ProcessingAttributes) -> ProcessingAttributes:
    """Processing attributes of NASC cells computed from Sv with ``sv_attributes``."""
    configuration = {
        "function": "shoalscope_proc.integration.nasc_time_cells",
        "upstream": sv_attributes.configuration_hash,
        **{k: float(v) for k, v in cells.attrs.items() if isinstance(v, (int, float))},
    }
    return ProcessingAttributes(
        level=Level.L4,
        software_version=sv_attributes.software_version,
        calibration_set=sv_attributes.calibration_set,
        environment_profile=sv_attributes.environment_profile,
        configuration_hash=configuration_hash(configuration),
    )
