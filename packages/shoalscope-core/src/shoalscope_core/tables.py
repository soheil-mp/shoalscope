"""Column contracts of the tables Shoalscope writes, shared by producers and storage.

A contract is plain data: names, logical types, units and meanings. Processing code builds rows
against it and storage code maps it to Iceberg and Arrow types, so the two never drift apart
and neither has to import the other. Units follow MacLennan et al. (2002).

Logical types: ``string``, ``int32``, ``double`` and ``timestamptz`` (UTC, microseconds).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal

__all__ = ["NASC_CELLS", "Column", "LogicalType", "TableContract"]

type LogicalType = Literal["string", "int32", "double", "timestamptz"]


@dataclass(frozen=True, slots=True)
class Column:
    """One column of a table contract."""

    name: str
    type: LogicalType
    description: str
    unit: str | None = None
    required: bool = True


@dataclass(frozen=True, slots=True)
class TableContract:
    """A table's namespace, name, columns and time-partition column."""

    namespace: str
    name: str
    columns: tuple[Column, ...]
    partition_by_day: str

    @property
    def identifier(self) -> str:
        """``namespace.name``."""
        return f"{self.namespace}.{self.name}"

    @property
    def names(self) -> tuple[str, ...]:
        """Column names in order."""
        return tuple(c.name for c in self.columns)


NASC_CELLS: Final = TableContract(
    namespace="l4",
    name="nasc_cells",
    partition_by_day="cell_start",
    columns=(
        Column("window_id", "string", "processing window the cell came from"),
        Column("channel_id", "string", "echosounder channel"),
        Column("frequency_hz", "double", "nominal frequency of the channel", "Hz"),
        Column("cell_start", "timestamptz", "start of the time cell (inclusive), UTC"),
        Column("cell_end", "timestamptz", "end of the time cell (exclusive), UTC"),
        Column("range_min_m", "double", "lower integration limit", "m"),
        Column("range_max_m", "double", "upper integration limit", "m"),
        Column("nasc_m2_per_nmi2", "double", "nautical area scattering coefficient", "m2 nmi-2"),
        Column("n_pings", "int32", "pings averaged in the cell"),
        Column("source_sha256", "string", "SHA-256 of the raw file the window was read from"),
    ),
)
"""L4 echo integration: NASC of every channel and time cell (roadmap M1.3)."""
