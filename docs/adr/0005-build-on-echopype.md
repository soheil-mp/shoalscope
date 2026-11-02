# 0005. Build on echopype; implement only the gaps

- Status: Accepted
- Date: 2026-11-02

## Context and problem statement

Converting Simrad raw files, calibrating them and gridding echograms are solved problems in
echopype (Apache-2.0, 0.12.0 on 2026-10-19), which follows the ICES SONAR-netCDF4 convention
and now includes noise masks, seabed and shoal detection, frequency differencing, MVBS and
NASC. What should Shoalscope implement itself?

## Decision drivers

- Do not re-implement mature, community-reviewed code.
- Fill the documented gaps that fish monitoring needs.
- Keep Shoalscope's own algorithms easy to offer upstream.

## Considered options

1. **echopype as the core dependency; Shoalscope implements the gaps** as separate modules.
2. Re-implement the whole chain for full control.
3. Contribute everything upstream first and build nothing locally.

## Decision outcome

Chosen: **option 1**. echopype does conversion, calibration (with Shoalscope's calibration
registry supplying values), noise masks, seabed and shoal detection, frequency differencing and
gridding. Shoalscope implements what echopype's own roadmap lists as open, or does not cover:

- split-beam single-target detection and Nv/M diagnostics (M7);
- fish tracking, track-based TS and passage counting (M8);
- sphere TS theory and the sphere-calibration workflow (M5.3, M5.4);
- profile-based sound speed and absorption (M5.6);
- SONAR-netCDF4 v2.0 Gridded and ICES AcMeta exports (M16);
- byte-range window reading and an EK80-style writer for the simulator (M3).

Those modules depend on xarray conventions compatible with echopype, not on Shoalscope's
platform code, so they can be proposed upstream (M5.8).

### Consequences

- Good: less code, and agreement with the wider community by construction.
- Bad: echopype's release cadence and API changes affect Shoalscope. Renovate pins the version,
  and a conformance suite (M3.9) catches regressions.
- Bad: echopype's Python range (≥ 3.13, < 3.15) constrains the toolchain (ADR-0014).

## More information

- [echopype development roadmap](https://github.com/echostack-org/echopype/blob/main/docs/source/contrib_roadmap.md)
