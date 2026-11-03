"""Echolevels processing levels and the processing attributes every dataset carries (ADR-0003).

Levels follow the Echolevels proposal for echosounder data
(https://echolevels.readthedocs.io/en/latest/levels_proposed.html). Each level maps to a storage
prefix and Iceberg namespace (``l1`` ... ``l4``); reference and operational data live under
``ref`` and ``ops``. If the proposal changes, only this module changes (with a new ADR).

Every dataset (Zarr group attributes) and every table write (Iceberg snapshot properties) carries
:class:`ProcessingAttributes`: level, software version, calibration set, environment profile and
a hash of the processing configuration, so any value can be traced to how it was made.
"""

from __future__ import annotations

import enum
import hashlib
import json
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final, Self

if TYPE_CHECKING:
    from collections.abc import Mapping

__all__ = [
    "ATTRIBUTE_PREFIX",
    "Level",
    "ProcessingAttributes",
    "configuration_hash",
]

ATTRIBUTE_PREFIX: Final = "shoalscope_"
"""Prefix of every processing attribute key in stored metadata."""

_HEX64 = re.compile(r"^[0-9a-f]{64}$")


class Level(enum.StrEnum):
    """Echolevels processing level."""

    L0 = "L0"
    L1A = "L1A"
    L1B = "L1B"
    L2A = "L2A"
    L2B = "L2B"
    L3A = "L3A"
    L3B = "L3B"
    L4 = "L4"

    @property
    def description(self) -> str:
        """What data at this level is."""
        return _DESCRIPTIONS[self]

    @property
    def prefix(self) -> str:
        """Storage prefix and Iceberg namespace, for example ``l2`` for L2A and L2B."""
        return self.value[:2].lower()


_DESCRIPTIONS: Final = {
    Level.L0: "raw instrument bytes as recorded",
    Level.L1A: "converted to a standard format, all instrument metadata kept",
    Level.L1B: "converted data with quality-control flags and corrections to metadata",
    Level.L2A: "calibrated volume backscattering strength (Sv) and target strength",
    Level.L2B: "calibrated data with noise and unwanted echoes removed",
    Level.L3A: "Sv averaged on a regular grid (MVBS)",
    Level.L3B: "gridded data classified into acoustic categories",
    Level.L4: "biological estimates: NASC, densities, targets, tracks and schools",
}


def configuration_hash(configuration: Mapping[str, object]) -> str:
    """SHA-256 of a configuration in canonical JSON (sorted keys, no whitespace).

    Examples:
    --------
    >>> configuration_hash({"b": 1, "a": [1, 2]}) == configuration_hash({"a": [1, 2], "b": 1})
    True
    """
    canonical = json.dumps(configuration, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


@dataclass(frozen=True, slots=True, kw_only=True)
class ProcessingAttributes:
    """How a dataset or table snapshot was made.

    Attributes:
        level: Echolevels level of the data.
        software_version: Version of the Shoalscope package that wrote it.
        calibration_set: Identifier of the calibration values used, for example ``file`` for
            the values stored in the raw file.
        environment_profile: Identifier of the sound speed and absorption used.
        configuration_hash: SHA-256 of the processing configuration (:func:`configuration_hash`).
    """

    level: Level
    software_version: str
    calibration_set: str
    environment_profile: str
    configuration_hash: str

    def __post_init__(self) -> None:
        """Validate the fields."""
        for name in ("software_version", "calibration_set", "environment_profile"):
            if not getattr(self, name):
                msg = f"{name} must not be empty"
                raise ValueError(msg)
        if not _HEX64.match(self.configuration_hash):
            msg = "configuration_hash must be 64 lower-case hexadecimal characters"
            raise ValueError(msg)

    def to_metadata(self) -> dict[str, str]:
        """String key-value pairs for Zarr attributes or Iceberg snapshot properties."""
        return {
            f"{ATTRIBUTE_PREFIX}level": self.level.value,
            f"{ATTRIBUTE_PREFIX}software_version": self.software_version,
            f"{ATTRIBUTE_PREFIX}calibration_set": self.calibration_set,
            f"{ATTRIBUTE_PREFIX}environment_profile": self.environment_profile,
            f"{ATTRIBUTE_PREFIX}configuration_hash": self.configuration_hash,
        }

    @classmethod
    def from_metadata(cls, metadata: Mapping[str, object]) -> Self:
        """Read the attributes back from stored metadata (other keys are ignored).

        Raises:
            KeyError: If an attribute is missing.
        """

        def get(name: str) -> str:
            return str(metadata[f"{ATTRIBUTE_PREFIX}{name}"])

        return cls(
            level=Level(get("level")),
            software_version=get("software_version"),
            calibration_set=get("calibration_set"),
            environment_profile=get("environment_profile"),
            configuration_hash=get("configuration_hash"),
        )
