# 0001. Record architecture decisions

- Status: Accepted
- Date: 2026-11-02

## Context and problem statement

Shoalscope spans acoustics, data engineering and operations, and will be built over many
months. Decisions made early (storage formats, transport, orchestration) shape everything after
them. How do we keep the reasons for those decisions visible?

## Decision outcome

Record every significant decision as an architecture decision record (ADR) in `docs/adr/`, in
the [MADR 4](https://adr.github.io/madr/) format, numbered in order. An accepted ADR is not
edited except to change its status; a new ADR supersedes it. The index in
[README.md](README.md) lists every ADR and its status.

A decision is significant when it is hard to reverse, affects more than one package, adds a
runtime service, or changes a data format or contract.

### Consequences

- Good: newcomers and reviewers can see why the system looks the way it does.
- Good: superseding, rather than editing, keeps the history honest.
- Bad: a little writing overhead for each decision.

## Confirmation

The definition of done in [ROADMAP.md](https://github.com/soheil-mp/shoalscope/blob/main/ROADMAP.md) requires an ADR whenever a recorded
decision changes.
