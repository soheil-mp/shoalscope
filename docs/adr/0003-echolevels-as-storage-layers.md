# 0003. Echolevels L0–L4 as the storage layers

- Status: Accepted
- Date: 2026-11-02

## Context and problem statement

Lakehouses are usually layered as bronze, silver and gold. Those names say little about sonar
data, where the community is defining processing levels of its own (Echolevels: L0 raw, L1A/B
converted, L2A/B calibrated and cleaned, L3A/B gridded, L4 biological estimates). How are
Shoalscope's datasets layered?

## Decision drivers

- Layers should mean the same thing to fisheries acousticians and data engineers.
- Each layer needs a clear contract and a retention rule.
- Products should be comparable with other echosounder pipelines.

## Considered options

1. **Echolevels L0–L4 as the layers**, mapped to storage prefixes and namespaces.
2. Generic bronze, silver and gold.
3. No formal layers.

## Decision outcome

Chosen: **option 1**. Storage prefixes, Icechunk repositories and Iceberg namespaces follow the
levels (`l1`, `l2`, `l3`, `l4`, plus `ref` for reference data and `ops` for operational data).
Every dataset and table carries processing attributes: level, software version, calibration
set, environment profile and configuration hash (M2.2). L0 raw bytes are read by range and are
not retained beyond a size-capped cache (ADR-0004).

### Consequences

- Good: the layer name tells a domain expert exactly what the data is.
- Good: retention and budgets are set per level.
- Neutral: Echolevels is a proposal and may change; the mapping lives in one module, and a
  change would get a new ADR.

## More information

- [Echolevels proposed levels](https://echolevels.readthedocs.io/en/latest/levels_proposed.html)
