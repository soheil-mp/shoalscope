# Contributing to Shoalscope

Thank you for considering a contribution. This guide covers how to set up, how changes are
made, and what "done" means here.

## Before you start

- Read the [README](README.md), the [architecture](docs/architecture.md) and the
  [roadmap](ROADMAP.md). Planned work is mirrored as
  [GitHub issues](https://github.com/soheil-mp/shoalscope/issues) grouped by milestone.
- For anything beyond a small fix, comment on the issue (or open one) first, so we agree on the
  approach before you write code.
- Everyone taking part follows the [code of conduct](CODE_OF_CONDUCT.md).

## Scope boundaries

Every change must stay within these limits:

- **No machine learning or AI in the product**: no model APIs, local models, embeddings, ML
  libraries, or datasets for training or evaluating models. Processing is physics, signal
  processing, estimation theory and cited rule tables
  ([ADR-0002](docs/adr/0002-deterministic-rule-based-processing.md)).
  `tools/check_dependencies.py` enforces this for dependencies.
- **No personal data.** Only synthetic data and public environmental data. Source metadata
  passes through allowlists ([ADR-0013](docs/adr/0013-privacy-allowlist-and-attribution.md)).
  Fixtures, examples and screenshots are synthetic.
- **Small data.** Never download whole raw files; read byte ranges within the data budgets
  ([ADR-0004](docs/adr/0004-small-data-by-design.md)). Never commit data files.
- **No secrets** in code or history. Configuration comes from environment variables; add every
  new variable to `.env.example` with a placeholder.
- **Permissive licences only** for dependencies (checked in CI). Never copy code you do not have
  the right to share.

## Set up

You need Git, [uv](https://docs.astral.sh/uv/) and [just](https://just.systems/)
(`uv tool install rust-just`). uv installs Python 3.13 itself.

```sh
just setup   # workspace, dev tools, git hooks
just check   # what CI runs: lint, import boundaries, dependency policy, types, tests
```

Or open the repository in the devcontainer (`.devcontainer/`), which runs `just setup` for you.

## Making a change

1. Create a branch from `main`: `feat/m3-window-planner`, `fix/idx-offsets`, `docs/...`.
2. Make small commits that each leave the tree working. Messages follow
   [Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`, `docs:`,
   `test:`, `refactor:`, `perf:`, `build:`, `ci:`, `chore:`. A hook checks this.
3. Run `just check` before pushing.
4. Open a pull request. The template asks for the roadmap item, testing notes and whether an ADR
   is needed. The `CI passed` check must be green.
5. Pull requests are merged with a merge commit. History on `main` is never rewritten: no
   squashing, no rebasing of pushed commits, no force-pushes.

## Code conventions

- **Layout:** workspace packages live in `packages/<name>/src/<module>`; tests live in
  `tests/unit`, `tests/integration` and `tests/e2e`.
- **Style:** Ruff formats and lints (line length 100); public functions have Google-style
  docstrings.
- **Types:** `mypy --strict` passes, with no unexplained `type: ignore`.
- **Boundaries:** import-linter contracts in `pyproject.toml` enforce the dependency rules of
  [ADR-0014](docs/adr/0014-python-toolchain-monorepo.md): `shoalscope-core` depends on nothing,
  the edge service never imports storage or connectors, the API never processes data.
- **Symbols and units:** follow MacLennan et al. (2002); SI units with the unit in the name
  (`range_m`, `sv_db`, `nasc_m2_per_nmi2`). Average in the linear domain, never in decibels.
- **Science:** every algorithm cites its source in its docstring and is scored against the
  simulator's ground truth before it runs on real data
  ([ADR-0012](docs/adr/0012-simulator-as-ground-truth.md)).
- **Determinism:** seed every random number generator; the same inputs give the same outputs.
- **Tests:** unit tests for logic, Hypothesis property tests for invariants, integration tests
  marked `@pytest.mark.integration`, and anything that touches the internet marked
  `@pytest.mark.network` (never part of the default run).

## Definition of done

A change is done when the [definition of done](ROADMAP.md#definition-of-done-every-item) in the
roadmap holds: merged with CI green, tested, typed, documented, contracts updated, no secrets or
personal data, budgets respected, ADR added if a recorded decision changed, and the roadmap item
ticked.

## Decisions

Significant technical decisions are recorded as ADRs in [docs/adr](docs/adr/README.md). Propose
a new ADR in your pull request when you change a technology, a boundary or a data contract.

## Roadmap and issues

`ROADMAP.md` is the source of truth for planned work. After changing it, a maintainer runs
`just roadmap-sync --apply` to create issues for new items and close issues for ticked ones.
