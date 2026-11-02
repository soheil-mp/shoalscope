# Working on Shoalscope

Context for coding assistants and contributors. Read [ROADMAP.md](ROADMAP.md) for what to build
next and [docs/architecture.md](docs/architecture.md) for how the parts fit.

## Scope boundaries

Every change must stay inside these boundaries:

- **No machine learning or AI in the product.** No calls to model APIs, no local models,
  embeddings or ML libraries, and no datasets for training or evaluating models. Processing is
  physics, signal processing, estimation theory and cited rule tables
  ([ADR-0002](docs/adr/0002-deterministic-rule-based-processing.md)).
- **No personal data.** Only synthetic data and public environmental data. Source metadata
  passes through allowlists; scientists' names, e-mail addresses and phone numbers in NOAA
  cruise metadata are never stored, logged or traced
  ([ADR-0013](docs/adr/0013-privacy-allowlist-and-attribution.md)). Fixtures, seeds, examples
  and screenshots are synthetic. No scraping of data about people.
- **No user accounts** and no storing of other people's data.
- **No security tooling** that finds or exploits vulnerabilities.
- **No secrets in code or history.** Read keys from environment variables; `.env` stays ignored;
  every new variable goes into `.env.example` with a placeholder.
- **Small data.** Never download whole raw files; read byte ranges within the budgets
  ([ADR-0004](docs/adr/0004-small-data-by-design.md)). Data never goes into Git.
- **Attribution.** Products built from OOI or NOAA data carry the citation those sources ask
  for. Raw OOI files are never redistributed.
- **Licences.** The project is MIT. Only add dependencies whose licences allow that (see
  [technology landscape §4](docs/research/03-technology-landscape.md#4-licence-policy-for-dependencies)),
  and never copy code we do not have the right to share.

## Git workflow

- Commit after each working step with a Conventional Commit message (`feat:`, `fix:`, `docs:`,
  `chore:`, `test:`, `refactor:`, `ci:`, `build:`, `perf:`).
- Never rewrite published history: no squashing, amending or rebasing pushed commits, and no
  force-push. Never change commit dates.
- Keep README.md and ROADMAP.md current when a change affects them; tick roadmap items when they
  are merged and run `scripts/sync_roadmap_issues.py --apply`.

## Engineering conventions

- Python 3.13, uv workspace, Ruff, `mypy --strict`, pytest with Hypothesis.
- Symbols and units follow MacLennan et al. (2002); SI units with suffixes in names
  (`range_m`, `sv_db`, `nasc_m2_per_nmi2`). Average in the linear domain, never in decibels.
- Every algorithm cites its source in its docstring and is tested against the simulator's
  ground truth before it is run on real data.
- Seed every random number generator; identical inputs must give identical outputs.
- Schemas and data contracts change before the code that uses them.
- Significant decisions get an ADR in `docs/adr/`.
