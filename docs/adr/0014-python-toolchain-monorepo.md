# 0014. Python 3.13 monorepo with uv workspaces, Ruff and strict mypy

- Status: Accepted
- Date: 2026-11-02

## Context and problem statement

Shoalscope has several deployable parts (edge service, consumer, pipelines, API) built on
shared libraries (raw I/O, simulator, processing). How is the code organised and which
toolchain does it use?

## Decision drivers

- Shared libraries with clear boundaries, deployable services with small images.
- One lock file and reproducible environments.
- Fast, strict feedback: formatting, linting and typing on every commit.
- Compatibility with echopype (Python ≥ 3.13, < 3.15) and dagster-dbt (< 3.14).

## Considered options

1. **A uv workspace monorepo on Python 3.13**, Ruff, mypy strict, pytest with Hypothesis.
2. Separate repositories per package.
3. Poetry or Pixi.

## Decision outcome

Chosen: **option 1**. Python 3.13 is the only version that satisfies both echopype 0.12 and
dagster-dbt 0.29. The workspace has these packages under `packages/`:

| Package | Role | May depend on |
| :-- | :-- | :-- |
| `shoalscope-core` | Domain types, units, acoustics equations, reference tables | — |
| `shoalscope-raw` | Simrad datagram reader and writer, index, byte-range windows | core |
| `shoalscope-sim` | Physics-based simulator | core, raw |
| `shoalscope-proc` | L1–L4 processing (wraps echopype) | core, raw |
| `shoalscope-ingest` | Source connectors, budgets, registry | core, raw |
| `shoalscope-lake` | Icechunk and Iceberg I/O, manifests, STAC | core |
| `shoalscope-edge` | Edge service and telemetry budget | core, raw, proc |
| `shoalscope-pipelines` | Dagster definitions | all libraries |
| `shoalscope-api` | FastAPI service and exports | core, lake |

import-linter enforces the "may depend on" column. Ruff formats and lints; mypy runs in strict
mode; pytest with Hypothesis, branch coverage failing under 85 %. The web app (`web/`) uses
TypeScript with Vite, Biome and Vitest.

### Consequences

- Good: one lock file, atomic changes across packages, boundaries enforced by a tool.
- Bad: the 3.13 pin waits for dagster-dbt to support 3.14; Renovate will flag it.
