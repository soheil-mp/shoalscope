"""Iceberg tables through PyIceberg (ADR-0007): catalogs, contract-driven schemas and writes.

The walking skeleton uses a local SQL catalog (SQLite) with a file-system warehouse, so it runs
without services; the Lakekeeper REST catalog of the Compose platform (M1.4) is a drop-in
replacement through :func:`pyiceberg.catalog.load_catalog`.

Schemas come from the column contracts in :mod:`shoalscope_core.tables`. Writes of a processing
window are idempotent: the window's rows replace any earlier rows with the same ``window_id`` in
one snapshot.
"""

from __future__ import annotations

import warnings
from contextlib import contextmanager
from typing import TYPE_CHECKING, Final

import pyarrow as pa
from pyiceberg.catalog.sql import SqlCatalog
from pyiceberg.expressions import EqualTo, Reference
from pyiceberg.expressions.literals import literal
from pyiceberg.partitioning import PartitionField, PartitionSpec
from pyiceberg.schema import Schema
from pyiceberg.transforms import DayTransform
from pyiceberg.types import DoubleType, IntegerType, NestedField, StringType, TimestamptzType

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping, Sequence
    from pathlib import Path

    from pyiceberg.catalog import Catalog
    from pyiceberg.table import Table
    from pyiceberg.types import PrimitiveType

    from shoalscope_core.tables import LogicalType, TableContract

__all__ = ["arrow_schema", "ensure_table", "iceberg_schema", "local_catalog", "replace_window"]

_ICEBERG: Final[dict[str, PrimitiveType]] = {
    "string": StringType(),
    "int32": IntegerType(),
    "double": DoubleType(),
    "timestamptz": TimestamptzType(),
}
_ARROW: Final[dict[str, pa.DataType]] = {
    "string": pa.string(),
    "int32": pa.int32(),
    "double": pa.float64(),
    "timestamptz": pa.timestamp("us", tz="UTC"),
}


def _logical(name: LogicalType) -> str:
    return name


def iceberg_schema(contract: TableContract) -> Schema:
    """Iceberg schema of a contract; field ids follow the column order from 1."""
    return Schema(
        *(
            NestedField(
                field_id=i,
                name=column.name,
                field_type=_ICEBERG[_logical(column.type)],
                required=column.required,
                doc=column.description + (f" [{column.unit}]" if column.unit else ""),
            )
            for i, column in enumerate(contract.columns, start=1)
        )
    )


def arrow_schema(contract: TableContract) -> pa.Schema:
    """Arrow schema of a contract, matching :func:`iceberg_schema`."""
    return pa.schema(
        [
            pa.field(c.name, _ARROW[_logical(c.type)], nullable=not c.required)
            for c in contract.columns
        ]
    )


@contextmanager
def local_catalog(directory: Path, name: str = "local") -> Iterator[SqlCatalog]:
    """A SQLite catalog with its warehouse under ``directory``, created if needed.

    The catalog's database connections are closed when the ``with`` block ends.
    """
    directory.mkdir(parents=True, exist_ok=True)
    warehouse = directory / "warehouse"
    warehouse.mkdir(exist_ok=True)
    catalog = SqlCatalog(
        name, uri=f"sqlite:///{directory / 'catalog.db'}", warehouse=warehouse.as_uri()
    )
    try:
        yield catalog
    finally:
        catalog.engine.dispose()


def ensure_table(catalog: Catalog, contract: TableContract) -> Table:
    """Create the contract's namespace and table (partitioned by day) if they do not exist."""
    catalog.create_namespace_if_not_exists(contract.namespace)
    schema = iceberg_schema(contract)
    source_id = schema.find_field(contract.partition_by_day).field_id
    spec = PartitionSpec(
        PartitionField(
            source_id=source_id,
            field_id=1000,
            transform=DayTransform(),
            name=f"{contract.partition_by_day}_day",
        )
    )
    return catalog.create_table_if_not_exists(
        contract.identifier, schema=schema, partition_spec=spec
    )


def replace_window(
    table: Table,
    contract: TableContract,
    window_id: str,
    rows: Sequence[dict[str, object]],
    *,
    properties: Mapping[str, str] | None = None,
) -> int:
    """Replace every row of ``window_id`` with ``rows`` in one snapshot; returns its id.

    ``properties`` become the snapshot's summary properties; pass the processing attributes
    (``ProcessingAttributes.to_metadata()``, ADR-0003) so every write records how it was made.

    Raises:
        ValueError: If a row does not have exactly the contract's columns or names another
            window.
    """
    for row in rows:
        if tuple(row) != contract.names:
            msg = f"row columns {tuple(row)} do not match the contract {contract.names}"
            raise ValueError(msg)
        if row["window_id"] != window_id:
            msg = f"row of window {row['window_id']!r} passed for window {window_id!r}"
            raise ValueError(msg)
    data = pa.Table.from_pylist(list(rows), schema=arrow_schema(contract))
    same_window = EqualTo(term=Reference("window_id"), value=literal(window_id))
    with warnings.catch_warnings():
        # The first write of a window has nothing to replace; PyIceberg warns about that.
        warnings.filterwarnings("ignore", "Delete operation did not match any records")
        table.overwrite(
            data, overwrite_filter=same_window, snapshot_properties=dict(properties or {})
        )
    snapshot = table.current_snapshot()
    if snapshot is None:  # pragma: no cover - overwrite always creates a snapshot
        msg = "the write created no snapshot"
        raise RuntimeError(msg)
    return int(snapshot.snapshot_id)
