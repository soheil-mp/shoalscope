# Architecture decision records

Significant decisions are recorded here in the [MADR 4](https://adr.github.io/madr/) format.
An ADR is never edited after it is accepted, except to change its status; a new ADR supersedes
it.

| ADR | Title | Status |
| :-- | :-- | :-- |
| [0001](0001-record-architecture-decisions.md) | Record architecture decisions | Accepted |
| [0002](0002-deterministic-rule-based-processing.md) | Deterministic, rule-based acoustic processing | Accepted |
| [0003](0003-echolevels-as-storage-layers.md) | Echolevels L0–L4 as the storage layers | Accepted |
| [0004](0004-small-data-by-design.md) | Small data by design: index-guided byte ranges, duty cycles and budgets | Accepted |
| [0005](0005-build-on-echopype.md) | Build on echopype; implement only the gaps | Accepted |
| [0006](0006-arrays-in-icechunk.md) | Echogram arrays in Icechunk (Zarr v3) | Accepted |
| [0007](0007-tables-in-iceberg.md) | Tables in Apache Iceberg with a Lakekeeper REST catalog | Accepted |
| [0008](0008-edge-transport-nats.md) | Edge processing and NATS JetStream transport with a telemetry budget | Accepted |
| [0009](0009-orchestration-dagster.md) | Dagster for orchestration and scheduling | Accepted |
| [0010](0010-transformations-dbt.md) | dbt-core on DuckDB for SQL transformations | Accepted |
| [0011](0011-schemas-and-data-contracts.md) | Contracts first: ODCS data contracts, Arrow schemas and Protobuf messages | Accepted |
| [0012](0012-simulator-as-ground-truth.md) | A physics-based simulator as the ground truth | Accepted |
| [0013](0013-privacy-allowlist-and-attribution.md) | Privacy allowlist for source metadata, and attribution by construction | Accepted |
| [0014](0014-python-toolchain-monorepo.md) | Python 3.13 monorepo with uv workspaces, Ruff and strict mypy | Accepted |

Planned ADRs, written when the milestone that needs them starts: Icechunk chunk shape (M11),
container base images (M19), Kubernetes packaging and GitOps (M20), observability stack (M21),
cloud provider for the demo (M22) and Rust acceleration (M23).

## Template

```markdown
# NNNN. Title

- Status: Proposed | Accepted | Superseded by NNNN
- Date: YYYY-MM-DD

## Context and problem statement
## Decision drivers
## Considered options
## Decision outcome
### Consequences
## Confirmation
## More information
```
