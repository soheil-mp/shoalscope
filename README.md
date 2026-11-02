# Shoalscope

Shoalscope monitors fish with scientific echosounders. It turns raw split-beam sonar data into
fish counts, tracks, sizes, densities per depth layer, school catalogues and daily migration
metrics, using only physics and published rules. It runs as a production-style data platform:
small-data ingestion from public ocean archives, an edge node that works over a poor link, a
versioned lakehouse, orchestration, data contracts and GitOps deployment.

> **Status:** planning is complete (2 November 2026); product code starts with milestone M0.5.
> The research, architecture, decisions and a 26-milestone roadmap are in this repository.

## What it does

- **Reads only the bytes it needs.** Raw echosounder files are 100–500 MB each. Shoalscope uses
  each file's ping index, or a timestamp search when there is none, to fetch single windows
  with HTTP range requests: about 2 MB for a minute of a 500 MB observatory file.
- **Finds and follows fish.** Calibrated Sv and TS, noise and seabed removal, split-beam
  single-target detection, multi-target fish tracking, passage counts, echo integration,
  schools and diel vertical migration. No machine learning: every result comes from an
  equation or a cited rule, and records which one.
- **Proves its accuracy.** A physics-based echosounder simulator writes realistic raw files
  with exact ground truth, so every algorithm is scored by closure tests.
- **Keeps every number traceable.** Echograms live in Icechunk, tables in Apache Iceberg, and a
  snapshot manifest links each published product to the exact source bytes, calibration,
  configuration and code that produced it.
- **Works at the edge.** An edge node processes pings next to the instrument and ships compact
  products over NATS within a byte budget per hour, surviving link outages.
- **Speaks the community's formats.** Echolevels processing levels, SONAR-netCDF4, ICES AcMeta,
  the ICES acoustic format, CF/ACDD, STAC and OGC API – EDR.

## Who it's for

- Fisheries and ocean scientists who want reproducible, open processing of observatory and
  survey echosounder data.
- Data and platform engineers who want a complete reference for a scientific data platform:
  ingestion, orchestration, lakehouse, data quality, observability and deployment.
- Operators of moored or autonomous echosounders who need processing on the device and a
  budgeted link.

## Data

Shoalscope works with public, non-personal environmental data, verified on 2026-11-02 (see
[data sources](docs/research/02-data-sources.md)):

- **OOI Oregon Offshore Cabled Shallow Profiler** echosounder (EK80, 38/120/200 kHz, 1 ping per
  second), a new 500 MB file about every four hours, plus CTDs on the same platform.
- **NOAA NCEI Water-Column Sonar Data Archive** on AWS, including the 2023 U.S.–Canada Pacific
  hake acoustic-trawl survey and its sphere-calibration files.
- **NOAA level-2 Zarr** echograms as an independent reference, and **ETOPO 2022** bathymetry.
- **Synthetic data** from the Shoalscope simulator for every test.

Default budgets keep the whole local lakehouse under 512 MiB. Data never goes into Git.

## Built with

| Area | Tools |
| :-- | :-- |
| Acoustics | Python 3.13, echopype, xarray, NumPy, SciPy, Numba, TEOS-10 (gsw) |
| Ingestion | obstore (HTTP and S3 byte ranges), dlt, a budget guard and a source registry |
| Storage | Icechunk (Zarr v3) for arrays, Apache Iceberg with Lakekeeper for tables, SeaweedFS (S3), PostgreSQL |
| Processing and SQL | Dagster (assets, partitions, sensors, schedules, checks), dbt-core on DuckDB, PyIceberg, Polars |
| Streaming | NATS JetStream leaf nodes, Protocol Buffers with Buf |
| Data quality | ODCS data contracts with datacontract-cli, Pandera, Dagster asset checks, ioos_qc, IOOS compliance-checker |
| Serving | FastAPI, pygeoapi (OGC API – EDR), xpublish, STAC; TypeScript, WebGL2, zarrita.js, DuckDB-WASM |
| DevOps | uv, Ruff, mypy, pytest, Hypothesis, pre-commit, GitHub Actions, Docker, k3d/k3s, Helm, Argo CD, SOPS, OpenTofu, OpenTelemetry, Grafana |

Choices and alternatives: [technology landscape](docs/research/03-technology-landscape.md) and
[architecture decision records](docs/adr/README.md).

## How to run it

The platform is not built yet; the first runnable slice is milestone M1. What runs today:

```sh
git clone https://github.com/soheil-mp/shoalscope.git
cd shoalscope

# Read one ping of a live 500 MB OOI file with three range requests (standard library only)
python3 examples/peek_raw_window.py

# Repository checks (secret scanning, spelling, Markdown, commit messages)
pipx install pre-commit   # or: uv tool install pre-commit
pre-commit install --hook-type pre-commit --hook-type commit-msg
pre-commit run --all-files

# Preview how the roadmap maps to GitHub issues (dry run, needs the GitHub CLI)
python3 scripts/sync_roadmap_issues.py
```

Once M1 lands, the whole slice will run with:

```sh
cp .env.example .env
just up      # SeaweedFS, PostgreSQL, Lakekeeper, Dagster, API
just e2e     # simulate, process, store, query, compare with ground truth
```

## Status and plans

| Phase | Milestones | Release |
| :-- | :-- | :-- |
| Foundations and walking skeleton | M0–M1 | v0.1.0 |
| Physics, formats and simulation | M2–M4 | v0.2.0 |
| Acoustic processing | M5–M9 | v0.3.0 |
| Data platform | M10–M15 | v0.4.0 |
| Standards and product surface | M16–M18 | v0.5.0 |
| Production engineering | M19–M22 | v0.6.0 |
| Validation, performance and 1.0 | M23–M25 | v1.0.0 |

The full plan, with 238 estimated items (916 hours), is in [ROADMAP.md](ROADMAP.md), and every
open item is a GitHub issue. Background reading:

- [Fisheries acoustics research](docs/research/01-fisheries-acoustics.md)
- [Data sources](docs/research/02-data-sources.md)
- [Technology landscape](docs/research/03-technology-landscape.md)
- [Architecture](docs/architecture.md)
- [Architecture decision records](docs/adr/README.md)

## Acknowledgements

Data from the NSF Ocean Observatories Initiative and NOAA's National Centers for Environmental
Information. Shoalscope builds on [echopype](https://github.com/echostack-org/echopype) and the
standards of the ICES Working Group on Fisheries Acoustics, Science and Technology.

## License

MIT, see [LICENSE](LICENSE).
