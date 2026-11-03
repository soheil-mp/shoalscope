# shoalscope-lake

Icechunk and Iceberg storage, snapshot manifests and the STAC catalogue.

Part of [Shoalscope](../../README.md). Planned work for this package is in
[ROADMAP.md](../../ROADMAP.md).

## Modules

| Module | What it does |
| :-- | :-- |
| `shoalscope_lake.iceberg` | Iceberg schemas from the column contracts in `shoalscope_core.tables`, a local SQLite catalog for laptops and tests, day-partitioned tables, and idempotent per-window writes (`replace_window`) |
