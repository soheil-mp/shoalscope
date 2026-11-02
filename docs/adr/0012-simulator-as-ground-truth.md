# 0012. A physics-based simulator as the ground truth

- Status: Accepted
- Date: 2026-11-02

## Context and problem statement

Real echosounder data has no ground truth: nobody knows exactly how many fish were in the beam
or where. Without truth, detection, tracking and density estimates can only be checked by eye.
Shoalscope must not use labelled datasets (ADR-0002). How are the algorithms verified?

## Decision drivers

- Exact, known answers for every algorithm.
- Reproducibility: the same seed gives the same data.
- Realistic enough to exercise real failure modes (noise, dense schools, seabed).
- Tests must not need real data in the repository.

## Considered options

1. **A physics-based echosounder simulator** that writes EK80-style raw files plus a
   ground-truth table, used for closure tests and accuracy metrics.
2. Manual inspection of real echograms.
3. Comparison with commercial software output only.

## Decision outcome

Chosen: **option 1** (M4). The simulator models the transducer beam, propagation, absorption,
TVG, fish with TS–length and tilt-dependent TS, Rayleigh-distributed echo amplitudes, schools,
diel vertical migration, plankton layers, the seabed, platform motion and noise artefacts. It
writes files that echopype opens unchanged, so the full pipeline is tested end to end. Real
data is still used, but for agreement checks with independent pipelines (NOAA level-2 Zarr,
instrument `.bot` lines, sphere theory) rather than as truth.

Closure tests are the backbone: integrating simulated scatterers must return the inserted
density; detecting simulated single targets must return their TS; tracking must return their
tracks (with CLEAR-MOT and HOTA scores).

### Consequences

- Good: every accuracy claim has a number behind it, and regressions are caught in CI.
- Bad: the simulator is a model of reality; its gaps are documented (M4.12) and real-data
  agreement checks (M24) guard against over-fitting to it.
- Neutral: synthetic files double as the only test fixtures, which keeps real data out of Git.
