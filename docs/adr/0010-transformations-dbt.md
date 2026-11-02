# 0010. dbt-core on DuckDB for SQL transformations

- Status: Accepted
- Date: 2026-11-02

## Context and problem statement

Above L4 rows, Shoalscope builds analysis-ready marts: daily densities per layer, migration
metrics, track summaries, survey NASC per EDSU, data-quality scorecards and budget usage. These
are SQL-shaped. How are they built and tested?

## Decision drivers

- Version-controlled, reviewed SQL with tests, contracts and documentation.
- Runs locally with no warehouse service.
- Integrates with the orchestrator's lineage.
- Open-source licence.

## Considered options

1. **dbt-core with dbt-duckdb** (Apache-2.0; 1.12.6 / 1.11.1).
2. SQLMesh.
3. Python-only transformations in Dagster assets.

## Decision outcome

Chosen: **option 1**. dbt runs on DuckDB attached to the Iceberg REST catalog (ADR-0007);
models are layered staging → intermediate → marts; marts have model contracts and dbt unit
tests; SQLFluff lints SQL; dagster-dbt exposes every model as an asset. Only dbt-core is used:
the dbt Fusion engine is source-available, not open source.

### Consequences

- Good: the most widely known transformation tool, with a mature testing story.
- Bad: materialising into an attached Iceberg catalog depends on DuckDB's Iceberg writes; the
  M1.6 spike decides the pattern (ADR-0007).
- Neutral: SQLMesh's virtual environments are attractive; Iceberg branches (M11.5) cover the
  reprocessing use case instead.
