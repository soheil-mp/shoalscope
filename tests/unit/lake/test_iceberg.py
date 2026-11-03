"""NASC rows into an Iceberg table through PyIceberg (roadmap M1.3)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest
from pyiceberg.transforms import DayTransform

from shoalscope_core.tables import NASC_CELLS
from shoalscope_lake.iceberg import (
    arrow_schema,
    ensure_table,
    iceberg_schema,
    local_catalog,
    replace_window,
)
from shoalscope_proc.integration import nasc_rows, nasc_time_cells
from shoalscope_proc.l2a import EnvironmentOverride, compute_sv
from shoalscope_sim.minimal import DEFAULT_CHANNEL, MinimalScenario, simulate

if TYPE_CHECKING:
    from pathlib import Path

T0 = datetime(2026, 1, 1, tzinfo=UTC)


def row(window_id: str = "w1", minute: int = 0, nasc: float = 10.0) -> dict[str, object]:
    start = T0 + timedelta(minutes=minute)
    return {
        "window_id": window_id,
        "channel_id": "ch1",
        "frequency_hz": 38_000.0,
        "cell_start": start,
        "cell_end": start + timedelta(minutes=1),
        "range_min_m": 1.0,
        "range_max_m": 40.0,
        "nasc_m2_per_nmi2": nasc,
        "n_pings": 60,
        "source_sha256": "0" * 64,
    }


def test_schemas_follow_the_contract() -> None:
    schema = iceberg_schema(NASC_CELLS)
    assert [f.name for f in schema.fields] == list(NASC_CELLS.names)
    assert [f.field_id for f in schema.fields] == list(range(1, len(NASC_CELLS.columns) + 1))
    assert str(schema.find_field("nasc_m2_per_nmi2").doc).endswith("[m2 nmi-2]")
    assert arrow_schema(NASC_CELLS).names == list(NASC_CELLS.names)
    assert NASC_CELLS.identifier == "l4.nasc_cells"


def test_table_is_partitioned_by_day(tmp_path: Path) -> None:
    with local_catalog(tmp_path) as catalog:
        table = ensure_table(catalog, NASC_CELLS)
        (field,) = table.spec().fields
        assert isinstance(field.transform, DayTransform)
        assert field.name == "cell_start_day"
    with local_catalog(tmp_path) as catalog:  # creating it again returns the same table
        again = ensure_table(catalog, NASC_CELLS)
        assert again.metadata.table_uuid == table.metadata.table_uuid


def test_windows_append_and_rewrites_are_idempotent(tmp_path: Path) -> None:
    with local_catalog(tmp_path) as catalog:
        table = ensure_table(catalog, NASC_CELLS)
        first = replace_window(table, NASC_CELLS, "w1", [row("w1", 0), row("w1", 1)])
        replace_window(table, NASC_CELLS, "w2", [row("w2", 2)])
        replace_window(table, NASC_CELLS, "w1", [row("w1", 0, nasc=20.0), row("w1", 1, nasc=20.0)])
        data = table.refresh().scan().to_arrow().sort_by("cell_start").to_pylist()
    assert [(r["window_id"], r["nasc_m2_per_nmi2"]) for r in data] == [
        ("w1", 20.0),
        ("w1", 20.0),
        ("w2", 10.0),
    ]
    assert data[0]["cell_start"] == T0
    assert first in {s.snapshot_id for s in table.snapshots()}


@pytest.mark.parametrize(
    ("rows", "message"),
    [([{"window_id": "w1"}], "do not match the contract"), ([row("w2")], "passed for window")],
)
def test_rejects_rows_that_break_the_contract(
    tmp_path: Path, rows: list[dict[str, object]], message: str
) -> None:
    with local_catalog(tmp_path) as catalog, pytest.raises(ValueError, match=message):
        replace_window(ensure_table(catalog, NASC_CELLS), NASC_CELLS, "w1", rows)


def test_simulated_window_end_to_end(tmp_path: Path) -> None:
    scenario = MinimalScenario()
    result = simulate(scenario, tmp_path / "sim.raw", tmp_path / "truth.parquet")
    sv = compute_sv(
        result.raw_path,
        environment=EnvironmentOverride(
            scenario.environment.sound_speed_mps, scenario.absorption_db_per_m
        ),
    )
    cells = nasc_time_cells(sv, cell_s=10.0, range_min_m=1.0)
    rows = nasc_rows(
        cells,
        window_id="sim-0001",
        source_sha256="1" * 64,
        frequency_hz={DEFAULT_CHANNEL.channel_id: DEFAULT_CHANNEL.frequency_hz},
    )
    assert len(rows) == 2
    assert rows[1]["cell_start"] == T0 + timedelta(seconds=10)
    with local_catalog(tmp_path / "lake") as catalog:
        table = ensure_table(catalog, NASC_CELLS)
        replace_window(table, NASC_CELLS, "sim-0001", rows)
        stored = table.refresh().scan().to_arrow().sort_by("cell_start").to_pylist()
    assert [r["nasc_m2_per_nmi2"] for r in stored] == pytest.approx(
        cells["nasc_m2_per_nmi2"].values[0].tolist()
    )
    assert {r["n_pings"] for r in stored} == {10}
