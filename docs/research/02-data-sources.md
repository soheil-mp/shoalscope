# Data sources

> Every source below was checked against the live service on 2026-11-02 with small listing
> or byte-range requests (nothing was bulk-downloaded). Sizes, paths and formats are what the
> services returned that day. Connectors must still treat all of them as untrusted input
> (M10).

## Summary

| # | Source | Format | Access | Role | Terms |
| :-- | :-- | :-- | :-- | :-- | :-- |
| 1 | NOAA NCEI Water-Column Sonar Data Archive (`s3://noaa-wcsd-pds`) | Simrad EK60/EK80 `.raw` with `.idx` and `.bot` sidecars; cruise metadata JSON | Anonymous S3 or HTTPS, byte ranges | Ship-survey fish data (Pacific hake survey 2023), sphere-calibration files | Free use and redistribution; no warranty |
| 2 | NOAA level-2 Zarr stores (`s3://noaa-wcsd-zarr-pds`) and STAC index (`s3://noaa-wcsd-pds-index`) | Zarr v3, Sv cube `[depth, time, frequency]`; STAC 1.1 | Anonymous HTTPS, chunk by chunk | Independent reference for validating Shoalscope's Sv | STAC collections declare MIT |
| 3 | OOI raw data archive, Oregon Offshore Cabled Shallow Profiler, 200 m platform (`CE04OSPS/PC01B/ZPLSCB102`) | Simrad EK80 `.raw` + `.idx`, new file about every 3 h 50 min | Anonymous HTTPS, byte ranges | Near-real-time observatory feed; replay source for the edge node | OOI Data Use Policy and User Terms: free use with required citation |
| 4 | OOI ERDDAP: CTDs on the same platform (`ooi-ce04osps-pc01b-4a-ctdpfa109`, `ooi-ce04osps-sf01b-2a-ctdpfa107`) | ERDDAP tabledap (CSV, Parquet, netCDF) with QARTOD flags | Anonymous HTTPS queries | Temperature and salinity for sound speed and absorption | Free use and redistribution; no warranty |
| 5 | NOAA ETOPO 2022, 15 arc-second (`ETOPO_2022_v1_15s` on CoastWatch ERDDAP) | griddap subsets | Anonymous HTTPS queries | Expected seabed depth for seabed-detection QC | Public NOAA data |
| 6 | Shoalscope simulator | EK80-style `.raw` + ground-truth Parquet | Generated locally, seeded | Ground truth for every algorithm; all test fixtures | Shoalscope (MIT) |

No source needs an account or a key. Real data never goes into Git: tests use tiny synthetic
fixtures from source 6, and connector tests use a local fake server (M10.10).

## 1. NOAA water-column sonar archive

- **Bucket:** `noaa-wcsd-pds` (us-east-1), listed in the AWS Registry of Open Data as "NOAA
  Water-Column Sonar Data Archive". Anonymous access works over HTTPS
  (`https://noaa-wcsd-pds.s3.amazonaws.com/...`) and with `--no-sign-request`.
- **Licence text:** "The data may be used and redistributed for free, but it is not intended
  for legal use because it may contain inaccuracies."
- **Layout:** `data/raw/<Ship_Name>/<CRUISE>/<INSTRUMENT>/<file>`, with sibling folders such
  as `<INSTRUMENT>_calibration/` and `metadata/`. More than 60 ship folders exist, from
  `Albatross_Iv` to `Okeanos_Explorer`.
- **Fish-survey example, `Bell_M._Shimada/SH2306`:** the 2023 Joint U.S.–Canada Integrated
  Ecosystem and Pacific Hake Acoustic Trawl Survey (cruise metadata: 2023-06-15 to 2023-09-10,
  "Calibrated w/ calibration data", calibration on 26 June 2023).
  - `EK80/Hake-D20230804-T152252.raw` and its neighbours are about 100 MiB each and cover about
    4.5 minutes. The first 1,000 keys alone hold 103.5 GB, so whole-file downloads are out of
    the question.
  - `EK80_calibration/` holds sphere-calibration raw files (about 100 MiB each) with `.idx`
    (about 70 KiB) and `.bot` (about 79 KiB) sidecars.
  - `metadata/SH2306_EK80-metadata.json` (6 KiB) describes the cruise. **It contains personal
    data**: names, e-mail addresses, phone numbers and street addresses of scientists. The
    connector keeps only allowlisted fields
    ([ADR-0013](../adr/0013-privacy-allowlist-and-attribution.md)).
- **EK60 example, `Henry_B._Bigelow/HB0706`:** `.raw` files of 95–205 MB with `.idx` and `.bot`
  sidecars of 250–540 KiB.
- **Byte ranges:** a `Range: bytes=0-99` request returns `206 Partial Content` with the full
  size in `Content-Range` (105,305,912 bytes for the file above).
- **What Shoalscope uses:** a handful of 60-second windows from SH2306 transects, windows from
  the calibration files for M5.4, and the `.bot` files as the instrument's own seabed line for
  comparison (M6.5).

## 2. NOAA level-2 Zarr stores and STAC index

- **Zarr bucket:** `noaa-wcsd-zarr-pds` with prefixes `level_1/`, `level_2/`, `level_2a/`,
  `level_5/` and `spatial/`. Level 2 exists for at least Bell M. Shimada, David Starr Jordan,
  Henry B. Bigelow, Miller Freeman, New Horizon, Okeanos Explorer and Pisces cruises.
- **Example:** `level_2/Henry_B._Bigelow/HB0706/EK60/HB0706.zarr` is a **Zarr v3** group written
  by `echofish` 25.11.8 (2025-11-24) with `calibration_status: True`. Arrays:
  - `Sv`: float32, shape 2,499 × 251,807 × 4 (`depth`, `time`, `frequency`), chunks
    512 × 512 × 1 (1 MiB uncompressed), `bytes` + `blosc` codecs, unit dB;
  - coordinates `depth` (m), `time` (ns since 1970), `frequency` (Hz), and per-ping `bottom`,
    `latitude`, `longitude`, `speed`, `distance`.
- **STAC index:** `noaa-wcsd-pds-index/catalog/<CRUISE>/collection.json` (STAC 1.1.0) with a
  bounding box, time interval and `license: MIT`, plus thumbnails, GeoParquet track files and a
  PMTiles map of cruise tracks.
- **What Shoalscope uses:** individual 1 MiB chunks that overlap the raw windows it processes,
  to compare its own Sv with an independent pipeline (M24.2). Shoalscope never treats this as
  ground truth, because processing choices differ.

## 3. OOI raw data archive (cabled observatory)

- **Instrument:** `CE04OSPS-PC01B-ZPLSCB102`, the echosounder on the 200 m platform of the
  Oregon Offshore Cabled Shallow Profiler Mooring (platform CTD at 44.374° N, 124.956° W;
  ETOPO 2022 gives about 580 m water depth there).
- **Path:** `https://rawdata.oceanobservatories.org/files/CE04OSPS/PC01B/ZPLSCB102/YYYY/MM/DD/`.
  Folders exist through November 2026, and the instrument folder also has `Calibrations/` and
  `processed/`.
- **Files:** `ZPLSCB102-D20261001-T025438.raw` is 524,314,500 bytes, with a 756 KiB `.idx`;
  a new pair starts about every 3 h 50 min (six on 2026-10-01).
- **Byte ranges:** the nginx server answers `Range` requests with `206 Partial Content` and
  `Accept-Ranges: bytes`, and sends `ETag` and `Last-Modified` for change detection.
- **Content (first 64 KiB parsed on 2026-11-02):**
  - written by Simrad **EK80** software; the first datagram is a 6,288-byte `XML0`
    configuration;
  - three channels: 38 kHz (`ES38-18DK-Split`), 120 kHz (`ES120-7CD`) and 200 kHz
    (`ES200-7CD`);
  - datagram types `XML0`, `FIL1` (filter coefficients), `NME0` (NMEA), `MRU0` (motion),
    `RAW3` (sample data) and `RAW4`;
  - the `.idx` file is a stream of 48-byte `IDX0` datagrams, one per ping cycle, each holding
    the ping time and the byte offset of that ping in the `.raw` file. Offsets advance by about
    31.7 KB per second.
- **Consequence:** one second of three-channel data is about 32 KB, so a 60-second window is
  about 2 MB of a 500 MB file. Shoalscope reads the index, then fetches only the byte ranges it
  needs ([ADR-0004](../adr/0004-small-data-by-design.md)).
- **Terms:** OOI has no open-data licence; use is governed by the OOI Data Use Policy
  (1102-00010) and User Terms (1102-00020), which require attribution in OOI's citation format.
  Shoalscope stores only derived products, never redistributes raw files, and generates the
  required citation for every product built from OOI data (M16.7).

## 4. OOI ERDDAP: co-located CTD

- **Server:** `https://erddap.dataexplorer.oceanobservatories.org/erddap`.
- **`ooi-ce04osps-pc01b-4a-ctdpfa109`:** CTD on the same 200 m platform as the echosounder.
  Data ran to 2026-11-02T03:34Z when checked: it is near-real-time.
- **`ooi-ce04osps-sf01b-2a-ctdpfa107`:** CTD on the shallow profiler, which moves between the
  200 m platform and the surface, so it gives full water-column profiles for sound speed and
  absorption. Data ran to 2026-08-03 when checked.
- **Variables:** temperature (°C), practical salinity, pressure, density, oxygen and
  conductivity, each with a `_qc_agg` aggregate QARTOD flag and a `_qc_tests` bitfield.
- **Example query (works):**
  `tabledap/ooi-ce04osps-sf01b-2a-ctdpfa107.csv?time,z,sea_water_temperature_profiler_depth_enabled,sea_water_practical_salinity_profiler_depth_enabled&time>=2026-08-01T00:00:00Z&time<=2026-08-01T00:05:00Z`
  returned one row per minute (about 8.18 °C and 33.91 at 196 m).
- **Ingestion:** with dlt, using an incremental cursor on `time` (M10.5).

## 5. Bathymetry: NOAA ETOPO 2022

- `https://coastwatch.pfeg.noaa.gov/erddap/griddap/ETOPO_2022_v1_15s`: a 15 arc-second global
  relief grid. A 2 × 2-cell query at the OOI site returned depths of 578–602 m.
- Used only as an expected seabed for QC of seabed detection along NOAA survey tracks (M15.4),
  fetched as small bounding boxes and cached.

## 6. Synthetic data

The Shoalscope simulator (M4) writes EK80-style raw files from a seeded scenario (fish,
schools, migration, noise, seabed) and a ground-truth table of every target and track. It is
the only source of test fixtures and the reference for every accuracy metric
([ADR-0012](../adr/0012-simulator-as-ground-truth.md)).

## 7. Data budget

| Item | Size (measured) | Budget rule |
| :-- | :-- | :-- |
| OOI `.idx` per file | 756 KiB | Cached, LRU-evicted |
| OOI 60 s raw window, 3 channels | about 2 MB | Fetched into memory, discarded after L2 |
| NOAA hake 60 s raw window | about 22 MB (100 MiB per 4.5 min) | Fewer windows per day; fetched into memory |
| NOAA level-2 Zarr chunk | 1 MiB uncompressed | Only chunks overlapping processed windows |
| CTD day, one platform, 1 per minute | about 1,440 rows | Kept in full (tiny) |
| ETOPO bounding box | a few KiB | Cached |
| L3 cube, 3 channels, 30 s × 1 m cells, 200 m column | about 7 MB per day before compression | Retention by profile |

Default budgets (`.env.example`): 512 MiB stored in total and 256 MiB fetched per day in the
`dev` profile. At the default duty cycle of one 60-second OOI window every 30 minutes, the feed
fetches about 100 MB a day and stores well under 10 MB. Exceeding a budget stops ingestion
with an error; it never silently drops data (M10.7).

## 8. Attribution

- NOAA NCEI water-column sonar archive and level-2 Zarr: cite NOAA NCEI and the cruise.
- OOI: "NSF Ocean Observatories Initiative" in OOI's recommended format, naming the platform,
  instrument reference designator, date range and URL. Generated per product (M16.7).
- NOAA ETOPO 2022: cite NOAA NCEI.
