# 0011. Contracts first: ODCS data contracts, Arrow schemas and Protobuf messages

- Status: Accepted
- Date: 2026-11-02

## Context and problem statement

Data crosses many boundaries: edge to platform, connectors to the lakehouse, tables to dbt,
marts to the API and exports. Each boundary needs a schema that both sides agree on, and
quality rules that run automatically. How are schemas and contracts defined?

## Decision drivers

- One source of truth per dataset, versioned in Git and reviewed before code changes.
- Machine-checkable at build time and at runtime.
- Standard formats that tools understand.

## Considered options

1. **Open Data Contract Standard (ODCS) v3** for tables (schema, quality rules, service levels),
   generating Arrow schemas and Pandera models; **Protobuf with Buf** for messages; **JSON
   Schema** for configurations and reference tables.
2. Pydantic models as the only source of truth.
3. Avro with a schema registry for everything.

## Decision outcome

Chosen: **option 1**.

- `contracts/` holds one ODCS v3 YAML per table, tested with `datacontract-cli` in CI and at
  runtime (M15.1). Iceberg table definitions and Pandera schemas are generated from them.
- `proto/` holds message schemas; Buf lints them and blocks breaking changes.
- Processing configurations and reference tables (TS–length relationships, rule windows,
  sphere properties) have JSON Schemas and are versioned with citations (M2.6, M2.8).
- Schemas and contracts change in the same pull request as, or before, the code that uses
  them. Breaking changes bump a major version and get a migration note.

### Consequences

- Good: quality rules live next to schemas and are enforced in one place.
- Good: consumers can read the contract instead of the code.
- Bad: generation steps add tooling; they are wrapped in `just` recipes and checked in CI.
