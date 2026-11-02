# 0004. Small data by design: index-guided byte ranges, duty cycles and budgets

- Status: Accepted
- Date: 2026-11-02

## Context and problem statement

Raw echosounder files are large: about 100 MiB per 4.5 minutes for the NOAA hake survey and
about 500 MB per 3 h 50 min for the OOI observatory. A single cruise holds more than 100 GB.
Shoalscope runs on a laptop with little free storage. How does it use these sources without
downloading them?

## Decision drivers

- Fetch only the bytes that are needed; store only derived products.
- Keep scientific value: windows must be long enough for noise estimation and tracking.
- Make budget overruns impossible to miss.

## Considered options

1. **Index-guided byte-range windows on a duty cycle, under enforced budgets.**
2. Download whole files and delete them after processing.
3. Use only pre-gridded NOAA level-2 Zarr.

## Decision outcome

Chosen: **option 1**.

- Simrad `.raw` files are length-prefixed datagram streams. Where an `.idx` file exists (OOI,
  NOAA EK60 cruises), it lists each ping's byte offset: Shoalscope reads the index, plans the
  byte ranges for a time window plus the configuration header, and fetches only those with
  HTTP range requests (M3.3). A 60-second OOI window is about 2 MB of a 500 MB file.
- Where there is no index (the NOAA hake EK80 files), an interpolation search on datagram
  timestamps locates the window: each probe reads 256 KiB at a byte offset and resynchronises
  on the first valid datagram, recognised by its length, type and trailing length (M3.11). The
  derived time-to-offset points are cached, so later windows in the same file are direct.
- Archives are sampled on a duty cycle (default: 60 s every 30 min), the way autonomous
  echosounders sample the ocean (M10.9).
- Fetch and storage budgets are set per source, per run and per day. The planner checks the
  budget before fetching and fails closed (M10.7). Retention is set per level (M11.8).
- Level-2 Zarr is used only as an independent reference (option 3 alone would hide
  calibration and processing choices).

### Consequences

- Good: a day of observatory data costs about 100 MB of transfer and a few MB of storage.
- Good: the same window planner feeds both batch backfills and the edge replay.
- Bad: duty-cycled results miss events between windows; products state their duty cycle, and
  the edge node (ADR-0008) processes continuously where an instrument is attached.
- Bad: window boundaries depend on index files or timestamp search; the framing check on the
  first datagram of every range catches a wrong offset, and the window is quarantined if it
  still does not frame.

## Confirmation

Integration tests assert the bytes transferred per window. CI runs with a 20 MiB budget.
