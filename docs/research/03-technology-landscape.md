# Technology landscape and tool selection

> Versions were read from PyPI, npm and GitHub releases on 2026-11-02. They are the starting
> point; Renovate keeps them current once code exists (M0.7). Each choice lists the
> alternatives considered, and the major ones have an ADR.

## 1. Ecosystem facts that shaped the choices

| Fact (as of 2026-11-02) | Effect on Shoalscope |
| :-- | :-- |
| echopype 0.12.0 (2026-10-19) requires Python ≥ 3.13, < 3.15; it moved to the `echostack-org` organisation and now has seafloor and shoal detection, noise masks and Zarr 3 | Build on it rather than re-implementing conversion and calibration ([ADR-0005](../adr/0005-build-on-echopype.md)) |
| `dagster-dbt` 0.29.28 declares `requires-python <3.14` | Python baseline is **3.13**, the only version both echopype and Dagster's dbt integration support ([ADR-0014](../adr/0014-python-toolchain-monorepo.md)) |
| Icechunk 2 was announced on 2026-04-09; 2.3.1 is current (Apache-2.0); 1.0 shipped in July 2025 | Arrays live in Icechunk ([ADR-0006](../adr/0006-arrays-in-icechunk.md)) |
| NOAA publishes level-2 echograms as Zarr v3 with 512 × 512 chunks and a STAC 1.1 catalogue | Zarr v3 and STAC are the natural interchange formats |
| DuckDB added Iceberg table creation and inserts in 1.4.0, updates and deletes in 1.4.2 (positional deletes, unpartitioned tables), and later releases extended writes; DuckDB 2.0.0 shipped on 2026-10-21 | DuckDB reads Iceberg and can write simple tables; partitioned writes go through PyIceberg, and a spike confirms what dbt can materialise (M1.6, [ADR-0007](../adr/0007-tables-in-iceberg.md)) |
| Lakekeeper 0.14.2 (2026-10-25) is an Apache-2.0 Iceberg REST catalog written in Rust | Iceberg catalog of record |
| dlt's open-source Iceberg support uses a local SQL catalog; Iceberg over a REST catalog belongs to the commercially licensed dltHub | dlt lands API data as Parquet; Shoalscope commits it to Iceberg with PyIceberg |
| MinIO's community edition was archived in April 2026 | Local object storage is **SeaweedFS** (Apache-2.0); code only uses the S3 API |
| Material for MkDocs support ends on 2026-11-05 | Documentation uses **Zensical** (MIT), pinned, with a fallback |
| `soda-core` 4.x is published under a proprietary licence | Not used |
| The dbt Fusion engine is source-available, not open source | **dbt-core** (Apache-2.0) only |

## 2. Selected stack

### Languages and project tooling

| Concern | Choice | Version | Licence | Alternatives considered |
| :-- | :-- | :-- | :-- | :-- |
| Core language | Python | 3.13 | PSF | Rust for the datagram hot path later (M23.4) |
| Packaging, environments, workspaces | uv | 0.13.6 | MIT/Apache-2.0 | Poetry, PDM, Pixi |
| Lint and format | Ruff | 0.17.3 | MIT | flake8 + black + isort |
| Types | mypy (strict) | 2.4.1 | MIT | pyright; Astral `ty` (advisory) |
| Tests | pytest + Hypothesis | 9.2.0 / 6.170 | MIT / MPL-2.0 | — |
| Benchmarks | pytest-benchmark | 5.3.1 | BSD-2 | CodSpeed (stretch) |
| Import boundaries | import-linter | current | BSD-2 | — |
| Task runner | just | 1.59.0 | CC0 | Make |
| Commit hooks | pre-commit + gitleaks | 4.x / 8.30.1 | MIT | lefthook |
| Web front end | TypeScript, Vite, Biome, Vitest, Playwright | 7.0 / 8.3 / 2.6 / 5.1 / 1.64 | Apache-2.0 / MIT | ESLint + Prettier |

### Acoustics and numerical core

| Concern | Choice | Version | Licence | Notes |
| :-- | :-- | :-- | :-- | :-- |
| Sonar conversion, calibration, cleaning, gridding | echopype | 0.12.0 | Apache-2.0 | EK60/EK80 → SONAR-netCDF4-like xarray |
| Labelled arrays | xarray | 2026.9.0 | Apache-2.0 | DataTree for SONAR-netCDF4 groups |
| Array storage | zarr-python | 3.4.2 | MIT | Zarr v3 |
| Transactional array store | Icechunk | 2.3.1 | Apache-2.0 | Branches, tags, snapshots |
| Seawater properties | gsw (TEOS-10) | 3.6.23 | BSD-3 | Sound speed from CTD |
| Arrays and algorithms | NumPy, SciPy | 2.5 / 1.18 | BSD-3 | `ndimage`, `optimize.linear_sum_assignment`, `special.jv` |
| JIT for hot loops | Numba | 0.68.1 | BSD-2 | Single-target detection, tracking gates |
| DataFrames and columnar | Polars, PyArrow | 2.1.0 / 26.0.0 | MIT / Apache-2.0 | Tables in and out of Iceberg |
| Byte-range I/O | obstore, fsspec/s3fs | 0.12.1 / 2026.9.0 | MIT / BSD-3 | Range reads over HTTPS and S3 |
| CTD quality control | ioos_qc (QARTOD) | 3.0.0 | Apache-2.0 | Gross range, spike, flat line |
| netCDF conformance | IOOS compliance-checker | 6.1.0 | Apache-2.0 | CF and ACDD checks in CI |
| Catalogue | pystac | 1.15.2 | Apache-2.0 | STAC items for products |

No learned models anywhere. A dependency policy check blocks ML libraries by name
(scikit-learn, PyTorch, TensorFlow, JAX, ONNX Runtime, Hugging Face, OpenCV DNN, model APIs)
from M0.7 onwards ([ADR-0002](../adr/0002-deterministic-rule-based-processing.md)).

### Data platform

| Concern | Choice | Version | Licence | Alternatives considered |
| :-- | :-- | :-- | :-- | :-- |
| Edge-to-platform messaging | NATS JetStream with leaf nodes | server 2.15.2, nats-py 2.16.0 | Apache-2.0 | MQTT 5 (Mosquitto/EMQX), Apache Kafka 4, Zenoh — [ADR-0008](../adr/0008-edge-transport-nats.md) |
| Message schemas | Protocol Buffers + Buf | protobuf 7.x, buf 1.75 | BSD-3 / Apache-2.0 | Avro + schema registry, CBOR |
| Object storage (local) | SeaweedFS S3 gateway | 4.52 | Apache-2.0 | RustFS, Garage (AGPL), MinIO (archived) |
| Table format | Apache Iceberg (format v2; v3 when every engine in use supports it) | — | Apache-2.0 | DuckLake 1.0, Delta Lake — [ADR-0007](../adr/0007-tables-in-iceberg.md) |
| Iceberg catalog | Lakekeeper on PostgreSQL | 0.14.2 | Apache-2.0 | Apache Polaris, Nessie, SQL catalog |
| Iceberg writes | PyIceberg | 0.12.0 | Apache-2.0 | DuckDB `iceberg` extension for unpartitioned tables |
| Query engine | DuckDB | 2.0.0 | MIT | Polars SQL, Trino (too heavy for a laptop) |
| API ingestion | dlt (open source) | 1.32.0 | Apache-2.0 | Hand-written clients, Airbyte |
| Orchestration | Dagster (+ dagster-dbt, dagster-dlt) | 1.13.28 / 0.29.28 | Apache-2.0 | Airflow 3, Prefect 3 (used by Echodataflow) — [ADR-0009](../adr/0009-orchestration-dagster.md) |
| Transformations | dbt-core + dbt-duckdb | 1.12.6 / 1.11.1 | Apache-2.0 | SQLMesh — [ADR-0010](../adr/0010-transformations-dbt.md) |
| DataFrame validation | Pandera (Polars backend) | 0.35.0 | MIT | Great Expectations 1.x |
| Data contracts | Open Data Contract Standard v3 + datacontract-cli | cli 1.2.9 | Apache-2.0 / MIT | Hand-written YAML — [ADR-0011](../adr/0011-schemas-and-data-contracts.md) |
| SQL lint | SQLFluff | 4.5.0 | MIT | — |
| Lineage | OpenLineage + Marquez | openlineage-python 1.55.0 | Apache-2.0 | Dagster lineage only |

### Serving

| Concern | Choice | Version | Licence |
| :-- | :-- | :-- | :-- |
| HTTP API | FastAPI + Pydantic | 0.162.0 / 2.14.2 | MIT |
| OGC API – Environmental Data Retrieval | pygeoapi (xarray provider) | 0.24.0 | MIT |
| Zarr over HTTP | xpublish | 0.5.2 | Apache-2.0 |
| API contract tests | Schemathesis | current | MIT |
| Load tests | k6 (separate binary) | current | AGPL-3.0, not linked |
| Echogram rendering in the browser | zarrita.js + WebGL2 | 0.7.5 | MIT |
| In-browser tables | DuckDB-WASM over Parquet | 1.33 (dev) | MIT |
| Ops dashboards | Grafana (OTel LGTM image) | otel-lgtm 0.39.0 | AGPL-3.0, separate service |

### DevOps and platform

| Concern | Choice | Version | Licence | Alternatives considered |
| :-- | :-- | :-- | :-- | :-- |
| Containers | Docker / BuildKit, multi-stage, non-root, multi-arch | Docker 29 | Apache-2.0 | Podman |
| Local stack | Docker Compose with profiles | — | — | Tilt |
| Local Kubernetes | k3d (k3s in Docker) | 5.9.0 | MIT | kind, minikube |
| Edge runtime | k3s on arm64 (Raspberry Pi 5 class) | — | Apache-2.0 | balena, plain systemd |
| Kubernetes packaging | Helm + chart-testing + kubeconform | — | Apache-2.0 | Kustomize only |
| GitOps | Argo CD (app of apps) | 3.5.6 | Apache-2.0 | Flux |
| Secrets | SOPS + age | 3.13.3 | MPL-2.0 | Sealed Secrets |
| Infrastructure as code | OpenTofu | 1.13.2 | MPL-2.0 | Terraform (BSL), Pulumi |
| Policy as code | Conftest (OPA/Rego) | — | Apache-2.0 | Kyverno |
| Fault injection | Toxiproxy | — | MIT | tc/netem |
| Observability | OpenTelemetry SDK + Collector, Grafana LGTM | sdk 1.45.2 | Apache-2.0 | Prometheus + Jaeger |
| CI/CD | GitHub Actions (pinned SHAs, least privilege) | — | — | — |
| Releases | release-please + Conventional Commits | 5.0.0 | Apache-2.0 | semantic-release |
| Supply chain | Syft SBOM, Cosign keyless signing, build provenance attestations, OpenSSF Scorecard | 1.56 / 3.1.4 / — / 2.5.0 | Apache-2.0 | — |
| Dependency updates | Renovate | — | AGPL-3.0 (hosted app) | Dependabot |
| Documentation | Zensical, Diátaxis structure, ADRs in MADR format | 0.0.74 | MIT | MkDocs Material (support ending), Sphinx |
| Reproducible reports | Quarto | current | MIT | Jupyter Book |

## 3. Algorithms

Everything is deterministic physics, signal processing or estimation theory
([ADR-0002](../adr/0002-deterministic-rule-based-processing.md)):

| Stage | Method | Reference | Implemented by |
| :-- | :-- | :-- | :-- |
| Sound speed | TEOS-10; Mackenzie nine-term equation as a cross-check | IOC et al. (2010); Mackenzie (1981) | gsw; Shoalscope |
| Absorption | Francois–Garrison | Francois & Garrison (1982) | Shoalscope (profile-based) |
| Calibrated Sv and TS | Simrad sonar equations | Simmonds & MacLennan (2005) | echopype |
| Sphere TS | Elastic-sphere modal series | Faran (1951); MacLennan (1981) | Shoalscope |
| Background noise | Noise estimate and subtraction with an SNR mask | De Robertis & Higginbottom (2007) | echopype |
| Impulse, transient, attenuated signal | Ping-neighbourhood comparisons | Ryan et al. (2015) | echopype |
| Seabed | Threshold and Blackwell-style split-beam methods; dead zone | Ona & Mitson (1996) | echopype + Shoalscope rules |
| Single targets | Pulse-length, beam-compensation and phase-stability criteria | Soule et al. (1997); Ona (1999) | Shoalscope |
| Detection diagnostics | Nv, M index | Sawada et al. (1993); Gauthier & Rose (2001) | Shoalscope |
| Motion compensation | Heave, pitch and roll from `MRU0` | Handegard et al. (2005) | Shoalscope |
| Tracking | Alpha–beta and Kalman filters, χ² gating, optimal assignment, M-of-N confirmation | Blackman (1986); Kalman (1960); Kuhn (1955) | Shoalscope |
| Tracking metrics | CLEAR-MOT, HOTA | Bernardin & Stiefelhagen (2008); Luiten et al. (2021) | Shoalscope |
| Echo integration | NASC per EDSU or time cell | MacLennan et al. (2002) | echopype + Shoalscope cells |
| Acoustic categories | Relative frequency response, dB-difference windows | Korneliussen & Ona (2003) | echopype + rule table |
| Schools | SHAPES-style and MOVIES-B-style detection; ICES descriptors | Coetzee (2000); Weill et al. (1993); Reid (2000) | echopype + Shoalscope |
| Vertical distribution | Centre of mass, inertia, occupancy, aggregation index, equivalent area | Urmy et al. (2012) | Shoalscope |
| Solar elevation | Low-precision solar position | Meeus (1998) | Shoalscope |
| Simulation | Sonar equation, circular-piston beam, Rayleigh-distributed echo amplitudes, Poisson noise processes | Medwin & Clay (1998); Simmonds & MacLennan (2005) | Shoalscope |
| Anomaly bands for data quality | Robust z-scores (median and MAD) | Standard robust statistics | Shoalscope |

Full references are in the [domain research](01-fisheries-acoustics.md#references), plus:

- Bernardin, K., & Stiefelhagen, R. (2008). Evaluating multiple object tracking performance:
  the CLEAR MOT metrics. *EURASIP Journal on Image and Video Processing*.
- Kalman, R. E. (1960). A new approach to linear filtering and prediction problems. *Journal of
  Basic Engineering* 82(1).
- Kuhn, H. W. (1955). The Hungarian method for the assignment problem. *Naval Research
  Logistics Quarterly* 2.
- Luiten, J., et al. (2021). HOTA: a higher order metric for evaluating multi-object tracking.
  *International Journal of Computer Vision* 129.

## 4. Licence policy for dependencies

- Shoalscope is MIT. Libraries linked into Shoalscope code must be MIT, BSD, Apache-2.0, ISC,
  MPL-2.0, PSF or similarly permissive.
- Copyleft services (Grafana, k6) may run **as separate processes**; they are never linked or
  vendored.
- No source-available or proprietary packages (Soda Core 4, the dbt Fusion engine, dltHub).
- A licence and scope check runs in CI from M0.7 onwards; new dependencies need a passing check.
