# 0002. Deterministic, rule-based acoustic processing

- Status: Accepted
- Date: 2026-11-02

## Context and problem statement

Interpreting echograms (finding fish, separating them from plankton and noise, sizing them) is
increasingly done with learned models. Shoalscope must produce numbers that scientists can
audit and that never depend on training data. How does it interpret echoes?

## Decision drivers

- Every output must be explainable by physics or by a written rule with a citation.
- Results must be reproducible bit for bit from the same inputs and configuration.
- No training data, labels or model weights may enter the project.
- Fisheries acoustics already has well-established deterministic methods.

## Considered options

1. **Physics, signal processing and estimation theory only**, with rule tables for categories.
2. Learned detectors and classifiers (for example CNNs on echograms).
3. A hybrid with rules first and models for hard cases.

## Decision outcome

Chosen: **option 1**. Shoalscope uses calibrated sonar equations, published noise-removal
algorithms, split-beam single-target criteria, Kalman and alpha–beta tracking, echo integration
and frequency-response rule tables (see the
[algorithm table](../research/03-technology-landscape.md#3-algorithms)). Classifications are
acoustic categories produced by versioned rule tables; every labelled cell, target and track
stores the identifier of the rule or parameter set that produced it.

### Consequences

- Good: every number can be explained, and every change of rule is visible in Git.
- Good: the simulator can verify every step against exact ground truth (ADR-0012).
- Bad: rule-based categories are coarser than species identification; Shoalscope reports
  acoustic categories, not species, and says so.
- Enforcement: the dependency policy (M0.7) fails CI on ML libraries, model runtimes and model
  API clients.

## Confirmation

The dependency check runs in pre-commit and CI. Reviews reject any learned component.
