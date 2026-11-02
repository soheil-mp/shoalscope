# 0009. Dagster for orchestration and scheduling

- Status: Accepted
- Date: 2026-11-02

## Context and problem statement

Shoalscope has batch backfills from archives, an observatory feed that grows every few hours,
an hourly CTD feed, nightly summaries, weekly maintenance and reprocessing campaigns. The
datasets have clear levels and partitions. Which orchestrator runs this?

## Decision drivers

- Data assets, not just tasks, as the unit of scheduling, with lineage.
- Partitions (per window, per day, per deployment) and backfills that respect budgets.
- Sensors for event-driven runs, schedules, freshness policies and asset checks for quality.
- Open source, runs locally and in Kubernetes, good Python testing story.

## Considered options

1. **Dagster** (Apache-2.0, 1.13.28).
2. Apache Airflow 3.
3. Prefect 3 (the engine behind Echodataflow).

## Decision outcome

Chosen: **option 1**. Every dataset is a software-defined asset grouped by Echolevels level.
OOI windows and NOAA files are dynamic partitions; CTD and summaries are daily partitions.
Sensors start runs on new OOI files, new CTD rows, landed edge batches and new calibration
sets. Asset checks implement the data-quality gates (ADR-0011, M15). dbt models and dlt
sources appear in the same graph through dagster-dbt and dagster-dlt.

### Consequences

- Good: lineage, partitions, checks and schedules in one model, testable in-process.
- Good: concurrency pools keep backfills within source budgets.
- Bad: `dagster-dbt` 0.29.28 requires Python < 3.14, which pins the baseline to 3.13
  (ADR-0014).
- Neutral: Echodataflow uses Prefect for echopype recipes; Shoalscope's needs (lakehouse,
  checks, partitions) favour Dagster's asset model.
