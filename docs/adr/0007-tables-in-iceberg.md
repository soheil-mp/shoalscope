# 0007. Tables in Apache Iceberg with a Lakekeeper REST catalog

- Status: Accepted
- Date: 2026-11-02

## Context and problem statement

Targets, tracks, NASC cells, densities, CTD profiles, calibration history and operational data
are tables. They need transactions, schema evolution, partitioning and time travel on
S3-compatible storage, readable by several engines. Which table format and catalog?

## Decision drivers

- An open, multi-engine standard (DuckDB, PyIceberg, Polars, Spark, Trino all read it).
- Snapshots that the array store's snapshots can be linked to (ADR-0006).
- A catalog that runs locally in a container and in Kubernetes.
- Permissive licences.

## Considered options

1. **Apache Iceberg with the Lakekeeper REST catalog** (Apache-2.0, 0.14.2), written by
   PyIceberg and read by DuckDB.
2. DuckLake 1.0 on PostgreSQL.
3. Delta Lake.

## Decision outcome

Chosen: **option 1**.

- Writes go through **PyIceberg** (partitioned appends and overwrite-by-partition). DuckDB's
  Iceberg write support is newer: updates and deletes arrived in 1.4.2 for unpartitioned
  tables only, and later releases are still extending it.
- Reads and SQL go through **DuckDB** attached to the REST catalog.
- **dbt** runs on DuckDB (ADR-0010). Which materialisations work against an attached Iceberg
  catalog with DuckDB 2.0 is confirmed by a spike in M1.6. If marts cannot be materialised
  there reliably, marts are written by a Dagster asset through PyIceberg from dbt-built
  relations; if the spike fails outright, the fallback is DuckLake, which is also driven
  through DuckDB, so the change stays contained.
- A **snapshot manifest** (M11.6) links each published product's Iceberg snapshot IDs to its
  Icechunk snapshot IDs, calibration set, environment profile, configuration hash and code
  version.

### Consequences

- Good: the most widely supported open table format, with a standard REST catalog API.
- Good: time travel and branches on both tables and arrays.
- Bad: more moving parts than DuckLake (a catalog service plus PostgreSQL).
- Bad: small-file maintenance (compaction, snapshot expiry) is Shoalscope's job (M11.7).

## Confirmation

The M1.6 spike records its result in this ADR's "More information" section or in a superseding
ADR.

## More information

- [Lakekeeper](https://github.com/lakekeeper/lakekeeper)
- [Writes in DuckDB-Iceberg](https://duckdb.org/2025/11/28/iceberg-writes-in-duckdb.html)
