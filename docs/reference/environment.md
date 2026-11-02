# Environment variables

Configuration comes from environment variables. Copy `.env.example` to `.env` and adjust it;
`.env` is never committed. Public data sources need no credentials.

| Variable | Default in `.env.example` | Used for |
| :-- | :-- | :-- |
| `SHOALSCOPE_PROFILE` | `dev` | Budget and retention profile: `dev`, `demo` or `ci` |
| `SHOALSCOPE_STORAGE_BUDGET_MIB` | `512` | Total bytes the local lakehouse may hold |
| `SHOALSCOPE_FETCH_BUDGET_MIB_PER_DAY` | `256` | Bytes fetched from sources per day |
| `SHOALSCOPE_CACHE_DIR` | `./cache` | Size-capped cache for index files and raw windows |
| `SHOALSCOPE_NOAA_WCSD_BUCKET` | `noaa-wcsd-pds` | NOAA water-column sonar archive |
| `SHOALSCOPE_NOAA_WCSD_ZARR_BUCKET` | `noaa-wcsd-zarr-pds` | NOAA level-2 Zarr stores |
| `SHOALSCOPE_OOI_RAW_BASE_URL` | OOI raw data archive | Observatory raw files |
| `SHOALSCOPE_OOI_ERDDAP_URL` | OOI ERDDAP | Co-located CTD data |
| `SHOALSCOPE_HTTP_USER_AGENT` | `shoalscope/0.0 (...)` | Identifies Shoalscope to data providers |
| `SHOALSCOPE_S3_ENDPOINT`, `_REGION`, `_ACCESS_KEY_ID`, `_SECRET_ACCESS_KEY`, `_BUCKET` | local SeaweedFS | Object storage |
| `SHOALSCOPE_ICEBERG_CATALOG_URI`, `SHOALSCOPE_ICEBERG_WAREHOUSE` | local Lakekeeper | Iceberg REST catalog |
| `LAKEKEEPER_PG_PASSWORD`, `LAKEKEEPER_ENCRYPTION_KEY` | placeholders | Catalog database and secret encryption |
| `SHOALSCOPE_ICECHUNK_PREFIX` | `icechunk` | Prefix of the Icechunk repositories |
| `SHOALSCOPE_NATS_URL`, `SHOALSCOPE_NATS_CREDS_FILE` | local NATS | Edge transport |
| `SHOALSCOPE_EDGE_TELEMETRY_BUDGET_BYTES_PER_HOUR` | `200000` | Edge uplink budget |
| `DAGSTER_HOME`, `DAGSTER_PG_PASSWORD` | `./.dagster`, placeholder | Orchestration |
| `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_SERVICE_NAME` | local collector | Telemetry |

Most of these are read from milestone M1 onwards; until then only the examples run.
