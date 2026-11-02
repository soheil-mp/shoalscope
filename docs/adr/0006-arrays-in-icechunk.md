# 0006. Echogram arrays in Icechunk (Zarr v3)

- Status: Accepted
- Date: 2026-11-02

## Context and problem statement

Calibrated and gridded echograms are dense arrays (time × range × channel). Tables are the
wrong shape for them, and plain Zarr on object storage has no transactions, so a crashed write
or a reprocessing campaign can leave a store half-updated. Where do L2B and L3 arrays live?

## Decision drivers

- Atomic, isolated writes and consistent reads on S3-compatible storage.
- Versioning: reprocess with a new calibration on a branch, compare, then merge or discard.
- Zarr v3 compatibility, so xarray, echopype and NOAA's level-2 stores share one model.
- Open licence, active project.

## Considered options

1. **Icechunk** (Apache-2.0; 2.3.1 current; Icechunk 2 announced 2026-04-09).
2. Plain Zarr v3 on S3 with a hand-made manifest.
3. netCDF files per window.
4. TileDB.

## Decision outcome

Chosen: **option 1**. One Icechunk repository per deployment and level, under the level's
prefix (ADR-0003). Reprocessing campaigns run on branches; releases are tags; every published
product records the Icechunk snapshot it read (M11.6). The chunk shape is chosen by benchmark
for both appends along time and echogram tile reads (M11.4). Plain Zarr v3 copies are exported
for the static web demo, because browsers read Zarr directly (M18.9).

### Consequences

- Good: snapshot isolation and time travel for arrays, matching what Iceberg gives tables.
- Good: branches make "what changed if we use the new calibration?" an ordinary workflow.
- Bad: browsers and some tools cannot read Icechunk directly; xpublish (M17.4) and exports
  bridge that.
- Bad: a newer project than Zarr itself; the version is pinned and upgrades are tested.

## More information

- [Icechunk](https://icechunk.io/)
