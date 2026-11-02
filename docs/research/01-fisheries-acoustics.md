# Fisheries acoustics: domain research

> Research for planning Shoalscope, compiled on 2026-11-02. It explains the science the
> platform implements, the processing chain it follows, what open tools already do, and where
> Shoalscope adds something new. Every algorithm Shoalscope uses is deterministic and cited;
> nothing in the product is learned from data ([ADR-0002](../adr/0002-deterministic-rule-based-processing.md)).

## 1. Why sonar for monitoring fish

Light fades within tens of metres in seawater, but sound travels kilometres. Scientific
echosounders send short pulses of sound and record the echoes from everything in the water
column: fish, zooplankton, bubbles and the seabed. Calibrated echoes become quantitative:
the strength of an echo depends on the size and anatomy of the scatterer (a fish's gas-filled
swimbladder returns most of its echo), and the summed echo energy from a volume of water is
proportional to how many scatterers it holds.

That makes active acoustics the standard tool for:

- **Stock assessment.** Acoustic-trawl surveys estimate the biomass of pelagic fish such as
  herring, sardine, pollock and Pacific hake. The 2023 Joint U.S.–Canada Integrated Ecosystem
  and Pacific Hake Acoustic Trawl Survey, whose raw data Shoalscope reads, is one example.
- **Long-term observation.** Moored and cabled echosounders record the water column for months
  and show diel vertical migration, seasonal change and episodic events.
- **Fish passage.** Side-looking sonar in rivers counts migrating fish such as salmon as they
  pass a fixed point.

It is non-invasive and continuous, and it samples the whole water column at once. The
trade-off is interpretation: an echogram shows *that* something scatters sound, not directly
*what* it is. The discipline has developed physics-based, rule-based methods to get from echoes
to fish densities, and those are what Shoalscope implements.

## 2. Instruments and deployments

| Instrument class | Examples | What it measures | In scope |
| :-- | :-- | :-- | :-- |
| Split-beam scientific echosounder, narrowband (CW) | Simrad EK60, EK80 (CW mode) | Calibrated Sv and TS at fixed frequencies (often 18–333 kHz) and the target's angle in the beam | **Yes, the core** |
| Split-beam, broadband (FM) | Simrad EK80 (FM mode) | Frequency spectra of Sv and TS after pulse compression | Stretch (M9.9) |
| Autonomous or moored echosounder | Simrad WBAT, ASL AZFP | As above, duty-cycled on battery | Via the same formats |
| Imaging sonar | ARIS, DIDSON | Acoustic video, used for counting fish in rivers | No: interpretation is usually manual or learned |
| Multibeam | Simrad ME70, MS70 | 3D school shapes | No |

Deployment shapes how the data must be processed:

| Deployment | Geometry | Main products | Shoalscope source |
| :-- | :-- | :-- | :-- |
| Ship survey | Down-looking, moving platform, transects | NASC per distance unit, density along track | NOAA hake survey (EK80, 2023) |
| Cabled or moored observatory | Fixed, continuous, often up-looking from a platform | Time series of vertical distribution, migration timing, target and track statistics | OOI Oregon Offshore Cabled Shallow Profiler, 200 m platform (EK80, 38/120/200 kHz, 1 ping per second) |
| River passage | Side-looking, horizontal beam across the flow | Counts of fish crossing, direction, size class | Synthetic only (M4.10, M8.8) |

## 3. Physics essentials

### 3.1 Quantities and symbols

Shoalscope uses the symbols and units of MacLennan, Fernandes & Dalen (2002):

| Symbol | Name | Unit | Meaning |
| :-- | :-- | :-- | :-- |
| σbs | Backscattering cross-section | m² | Echo strength of one target |
| TS | Target strength | dB re 1 m² | 10 log10(σbs) |
| sv | Volume backscattering coefficient | m⁻¹ | Sum of σbs per unit volume |
| Sv | Volume backscattering strength | dB re 1 m⁻¹ | 10 log10(sv) |
| sa | Area backscattering coefficient | m² m⁻² | ∫ sv dz over a depth layer |
| sA (NASC) | Nautical area scattering coefficient | m² nmi⁻² | 4π · 1852² · sa |
| MVBS | Mean volume backscattering strength | dB re 1 m⁻¹ | 10 log10 of the mean of sv in a cell |

Averages are always taken in the linear domain (sv, σbs) and converted to decibels afterwards;
averaging decibels is a classic source of bias, and Shoalscope's typed units make it hard to do
by accident (M2.3).

### 3.2 From voltage to Sv and TS

For a calibrated narrowband split-beam system, received power Pr becomes:

- **Sv** = Pr + 20 log R + 2αR − 10 log(Pt λ² c τ ψ G0² / 32π²) − 2 Sa,corr
- **TS** = Pr + 40 log R + 2αR − 10 log(Pt λ² G0² / 16π²)

where R is range, α the absorption coefficient, Pt transmit power, λ wavelength, c sound speed,
τ pulse duration, ψ the equivalent two-way beam angle, G0 the on-axis gain and Sa,corr the
integration correction found by calibration. The 20 log R and 40 log R terms are the
time-varied gain (TVG): volume scatterers fill a beam that widens with range, point targets do
not. echopype implements these equations for EK60 and EK80 data; Shoalscope adds per-range
sound speed and absorption from measured CTD profiles (M5.6) instead of a single
water-column average.

### 3.3 Sound speed and absorption

Sound speed varies with temperature, salinity and depth (about 1,450–1,550 m s⁻¹ in the ocean).
Shoalscope computes it from CTD data with TEOS-10 (`gsw`), and from the Mackenzie (1981)
equation as a cross-check. Absorption rises steeply with frequency (roughly 0.01 dB m⁻¹ at
38 kHz and several times that at 120 and 200 kHz), so a wrong α biases high-frequency Sv at
long range. Shoalscope uses Francois & Garrison (1982). Both come from public CTD profiles on
the same OOI platform as the echosounder (see [data sources](02-data-sources.md#4-ooi-erddap-co-located-ctd)).

### 3.4 Beam geometry

A circular transducer of radius a has the one-way pressure directivity
D(θ) = 2 J1(ka sin θ) / (ka sin θ), with k = 2π/λ. The two-way intensity factor that weights
an off-axis echo is D⁴. A split-beam transducer is divided into quadrants; the phase difference
between halves gives the alongship and athwartship angles of a single target, so its echo can
be compensated for beam position and its 3D position can be computed. Close to the transducer,
in the near field (commonly taken as πa²/λ), the far-field equations do not hold, and Shoalscope
excludes that range by rule.

### 3.5 Resolution and noise

Range resolution is about cτ/2: a 1.024 ms pulse at 1,480 m s⁻¹ resolves targets about 0.76 m
apart. Noise rises with range through TVG, so at long range, and especially at high frequency,
Sv is dominated by noise unless the background is estimated and removed. Every product records
its signal-to-noise ratio so users can see where the signal ends.

## 4. Processing chain and data levels

The echosounder community is converging on shared processing levels (Echolevels). Shoalscope
uses them directly as its storage layers ([ADR-0003](../adr/0003-echolevels-as-storage-layers.md)):

| Level | Definition (Echolevels) | Shoalscope stage | Methods |
| :-- | :-- | :-- | :-- |
| L0 | Raw manufacturer format | Raw windows read by byte range; never stored long-term | Simrad datagram reader (M3) |
| L1A | Converted to an open format, with ancillary data | Per-window datasets in SONAR-netCDF4 structure | echopype conversion, metadata allowlist |
| L1B | L1A after quality control, such as fixing time coordinates | Monotonic, de-duplicated ping times; QC flags | echopype `qc`, Shoalscope checks |
| L2A | Calibrated Sv/TS at native resolution, with split-beam angles | Calibrated windows; calibration set and environment recorded | Calibration registry, profile-based environment (M5) |
| L2B | L2A with noise, seabed and surface removed | Masks and cleaned Sv | Background, impulse, transient and attenuated-signal masks; seabed detection; exclusion zones (M6) |
| L3A | Regridded onto a common grid (for example MVBS) | Echogram cubes in Icechunk | echopype `commongrid` |
| L3B | L3A after further QC | Cubes with QC masks | Shoalscope QC (M15) |
| L4 | Biological estimates: NASC, classification labels, biomass, summaries | Targets, tracks, NASC cells, densities, schools, vertical-distribution metrics | M7–M9 |

## 5. Calibration

Echosounders drift with temperature, ageing and installation, so absolute numbers need
calibration. The standard method suspends a metal sphere of known target strength in the beam
and compares measured with theoretical TS (Foote et al. 1987; Demer et al. 2015). The sphere's
TS is computed from elastic scattering theory (Faran 1951; MacLennan 1981): a 38.1 mm
tungsten-carbide sphere has a TS of about −42.4 dB at 38 kHz. Calibration yields the on-axis
gain, the Sa correction, the beam angles and the angle offsets for each channel.

Consequences for Shoalscope:

- Calibration values are **versioned data**, not constants. Each L2 product records which
  calibration set it used, and reprocessing with a new set is an Icechunk branch (M5.1, M11.5).
- Both data sources publish calibration material: the NOAA hake cruise has an `EK80_calibration`
  folder of sphere-calibration raw files, and OOI publishes a calibration folder per
  echosounder. OOI's own report shows how much this matters: default versus recommended
  parameters changed mean Sv by 5 dB (Sato et al., OOI).
- The theoretical sphere model is implemented from first principles (M5.3). This is on
  echopype's list of open work.

## 6. Noise and artefacts

| Artefact | Cause | Treatment | Reference |
| :-- | :-- | :-- | :-- |
| Background noise | Electrical and flow noise, amplified by TVG | Estimate per ping block, subtract in the linear domain, mask below an SNR threshold | De Robertis & Higginbottom (2007) |
| Impulse noise | Interference from other acoustic instruments | Compare each ping with its neighbours | Ryan et al. (2015) |
| Transient noise | Short bursts over many pings | Compare a block with deeper or wider context | Ryan et al. (2015) |
| Attenuated signal | Bubbles under the hull in bad weather | Flag pings much weaker than their neighbours | Ryan et al. (2015) |
| Seabed and dead zone | The seabed echo hides fish just above it | Detect the seabed, exclude a backstep, record the dead-zone height | Ona & Mitson (1996) |
| Surface and near field | Bubbles, transducer near field | Exclude by range | Simmonds & MacLennan (2005) |
| False bottom | Seabed echo from the previous ping | Detect and mask | Simmonds & MacLennan (2005) |

echopype 0.12 implements most of these (`echopype.clean`, `echopype.mask.detect_seafloor`).
Shoalscope wraps them with typed, versioned configurations, records every mask as provenance,
and scores them against simulated ground truth (M6.8).

## 7. Single targets and in-situ target strength

A single fish far enough from its neighbours produces an isolated echo. Detecting those echoes
gives the fish's TS, its position in the beam and, by extension, its size class. Split-beam
single-target detection keeps an echo only if:

1. its compensated TS exceeds a threshold;
2. its pulse length, measured at a fixed level below the peak, stays within a window around the
   transmitted pulse length (overlapping echoes are longer);
3. the beam compensation is below a maximum (far off-axis echoes are unreliable);
4. the split-beam angles are stable across the samples of the echo (overlapping echoes
   produce erratic phase; Soule et al. 1997).

Detection is biased when fish are dense: two fish in the same resolution volume look like one
larger fish. Two diagnostics flag that risk: Nv, the expected number of fish in the sampled
volume (Sawada et al. 1993), and the M index (Gauthier & Rose 2001). Shoalscope computes both
for every detection batch and refuses to publish in-situ TS when they exceed their thresholds
(M7.5).

TS is converted to length through relationships of the form TS = 20 log L + b20 (Love 1971;
Foote 1987). These are uncertain: for Pacific hake, the long-used b20 of −68 dB (Traynor 1996)
was found to be 4–6 dB too high by Henderson & Horne (2007). Shoalscope therefore keeps
TS–length relationships in a cited, versioned reference table (M2.6) and reports size classes
with that table's identifier, never as a hidden constant.

echopype lists single-target detection as open work. Shoalscope implements it (M7) as a
separate, upstream-friendly module.

## 8. Tracking and counting fish

Successive detections of the same fish form a track. From range and the two beam angles a
target has a 3D position relative to the transducer; on a moving platform, heave, pitch and
roll from the motion sensor (EK80 `MRU0` datagrams) are removed first (Handegard et al. 2005).
Tracking then follows standard estimation theory: prediction with an alpha–beta or Kalman
filter, gating on the Mahalanobis distance, optimal assignment, and rules for starting and
ending tracks (Blackman 1986). Tracks give:

- one TS estimate per fish (averaged in the linear domain over the track), less noisy than
  single echoes;
- swimming speed and direction, and therefore behaviour such as avoidance or migration;
- **counts**: in a river, the number of tracks crossing a virtual line upstream and downstream.

Counting fish one by one (echo counting) works at low density; at higher density, echo
integration (section 9) takes over. Shoalscope computes both where both are valid, and the
comparison is itself a quality check (M9.4).

## 9. Echo integration and density

Echo integration sums sv over a cell, either an elementary distance sampling unit (EDSU; ICES
surveys use 1 nmi) for ships or a time interval for fixed platforms. With the mean σbs of the
fish present, from in-situ TS or a TS–length relationship and a length distribution, the
areal density is ρA = sA / (4π σ̄bs) fish per nmi². Shoalscope does not estimate stock biomass,
which needs trawl samples and survey design; it reports acoustic densities by acoustic category
and depth layer, with their assumptions attached.

## 10. Rule-based acoustic categories

Different scatterers respond differently across frequencies. The relative frequency response
r(f) = sv(f) / sv(38 kHz) (Korneliussen & Ona 2003) is roughly flat or falling for fish with
a swimbladder, rising for fish without one (such as mackerel), and rising steeply for small
fluid-like zooplankton such as krill. Simple dB-difference windows on Sv(120) − Sv(38) are
widely used in the same way. Shoalscope stores these windows as a versioned, cited rule table;
every labelled cell carries the rule identifier that produced it, and the labels are acoustic
categories, not species ([ADR-0002](../adr/0002-deterministic-rule-based-processing.md)).

## 11. Schools and aggregations

Pelagic fish often school. School detection finds connected regions of Sv above a threshold
with minimum height and length and linking distances (SHAPES, Coetzee 2000; MOVIES-B, Weill
et al. 1993); echopype 0.12 implements both styles in `echopype.mask.detect_shoal`. Shoalscope
adds the standard descriptors of each school (Reid 2000): morphometric (height, length, area,
perimeter), energetic (mean Sv, NASC), positional (depth, height above the seabed) and
multi-frequency (r(f)).

## 12. Vertical distribution and diel vertical migration

Many fish and their prey migrate vertically each day, usually rising at dusk and descending at
dawn. A continuous echosounder record makes that visible. Shoalscope summarises each profile
with the metrics of Urmy et al. (2012): centre of mass, inertia (spread), proportion of the
water column occupied, aggregation index and equivalent area. It times migration against
solar elevation computed with Meeus (1998), with no external service. The OOI cabled time
series is well suited to this.

## 13. Standards and conventions

| Standard | Status | Shoalscope use |
| :-- | :-- | :-- |
| MacLennan et al. (2002) symbols | Community standard | Names and units of every variable |
| ICES SONAR-netCDF4, v1.0 (ICES CRR 341, 2018) and v2.0 (GitHub release, 2022, adds a Gridded group) | Current | L1/L2 structure via echopype; L3 export to the v2.0 Gridded group (M16.1) |
| ICES AcMeta | Metadata convention for processed acoustic data | Metadata of every L3/L4 product (M16.3) |
| ICES acoustic data format | XML or CSV submissions with Cruise, Log, Sample, Data, Instrument, Calibration, DataAcquisition and DataProcessing records, ICES vocabularies, EDSU-based logs | Export of survey NASC (M16.4) |
| Echolevels | Proposed processing levels L0–L4 | Storage layers ([ADR-0003](../adr/0003-echolevels-as-storage-layers.md)) |
| CF conventions and ACDD | General netCDF metadata | Checked with the IOOS compliance-checker (M15.9) |
| STAC 1.1 | Catalogue of spatio-temporal assets | Catalogue of Shoalscope products; NOAA publishes its level-2 Zarr stores in STAC too |

## 14. Prior art and the gap Shoalscope fills

| Project | Licence | What it does | Relation to Shoalscope |
| :-- | :-- | :-- | :-- |
| [echopype](https://github.com/echostack-org/echopype) 0.12.0 (2026-10-19) | Apache-2.0 | Converts raw files to SONAR-netCDF4-like xarray/Zarr; calibration; noise removal; seafloor and shoal detection; frequency differencing; MVBS and NASC | Core dependency ([ADR-0005](../adr/0005-build-on-echopype.md)) |
| [Echodataflow](https://github.com/OSOceanAcoustics/echodataflow) | Apache-2.0 | Prefect-based "recipes" that run echopype stages (Staneva et al., SciPy 2024) | Orchestrates echopype; no lakehouse, contracts, tracking or edge |
| [Echoregions](https://github.com/echostack-org/echoregions), Echoshader, Echopop | Apache-2.0 | Region files, interactive plots, hake biomass with trawl data | Possible later integrations |
| NOAA CI-CMG [water-column-sonar-processing](https://github.com/CI-CMG/water-column-sonar-processing) ("echofish") | MIT | Converts the NCEI archive to level-1/level-2 Zarr and serves a web viewer | Shoalscope reads its level-2 Zarr as a reference (M10.3, M24.2) |
| pyEcholab (NOAA AFSC), Echopy | MIT | Raw file reading and noise algorithms in Python | Algorithm references |
| ESP3 (NIWA), StoX (IMR) | Open source | Desktop processing (MATLAB) and survey estimation | Workflow references |
| Echoview, LSSS, Sonar5-Pro | Commercial | Full desktop processing suites | The de facto standard Shoalscope must agree with in principle |

Two things stand out from this survey:

1. **The algorithm gaps are documented.** echopype's development roadmap lists, as not yet
   done: single-target detection, standard-target (sphere) calibration, updated sound speed and
   absorption, profile-based Sv and TS, the SONAR-netCDF4 v2.0 Gridded group and AcMeta. Fish
   tracking is not on it at all. These are exactly what fish monitoring needs.
2. **There is no open, production-grade data platform for continuous sonar.** Existing open
   tools are libraries, notebooks or batch converters. None combines contract-checked storage
   layers, lineage, data-quality gates, edge processing with a telemetry budget, and GitOps
   deployment, and none is designed to work on a laptop-sized storage budget against
   multi-hundred-megabyte raw files.

## 15. What Shoalscope adds

1. **Index-guided byte-range ingestion.** Raw Simrad files are sequences of length-prefixed
   datagrams, and the matching `.idx` files list each ping's byte offset (verified on OOI and
   NOAA files, see [data sources](02-data-sources.md)). Shoalscope reads only the pings it
   needs with HTTP range requests: about 2 MB for a 60-second window of a 500 MB file.
2. **Duty-cycled sampling of archives**, as autonomous echosounders sample the ocean, under
   enforced fetch and storage budgets ([ADR-0004](../adr/0004-small-data-by-design.md)).
3. **The missing fish algorithms**: split-beam single-target detection with Nv/M diagnostics,
   multi-target fish tracking with motion compensation, track-based TS and passage counts,
   sphere TS theory and profile-based environment.
4. **A physics-based echosounder simulator** that writes valid EK80-style raw files with exact
   ground truth, so every algorithm is verified by closure tests rather than by eye
   ([ADR-0012](../adr/0012-simulator-as-ground-truth.md)).
5. **A two-format lakehouse**: echogram cubes in Icechunk (transactional Zarr) and tables in
   Apache Iceberg, tied together by a snapshot manifest so each published number traces back
   to the exact arrays, calibration set and code version that produced it
   ([ADR-0006](../adr/0006-arrays-in-icechunk.md), [ADR-0007](../adr/0007-tables-in-iceberg.md)).
6. **Echolevels as storage layers**, instead of generic bronze, silver and gold tiers.
7. **Edge processing with a telemetry budget**: an edge node reduces pings to targets, tracks
   and NASC cells and ships them over an intermittent link within a byte budget per hour
   ([ADR-0008](../adr/0008-edge-transport-nats.md)).
8. **Standard exports**: SONAR-netCDF4 v2.0 Gridded, ICES AcMeta, the ICES acoustic format,
   CF/ACDD and STAC, all validated in CI.

## 16. Non-goals

- No machine learning: no species classifiers, no learned detectors, no training data.
- No stock assessment or management advice; densities are reported with their assumptions.
- No imaging-sonar (ARIS/DIDSON) processing.
- No personal data: source metadata is filtered through an allowlist
  ([ADR-0013](../adr/0013-privacy-allowlist-and-attribution.md)).

## 17. Glossary

- **Echogram:** image of echo strength against time (ping) and range.
- **EDSU:** elementary distance sampling unit, the along-track interval over which NASC is
  reported (1 nmi in ICES surveys).
- **Ping:** one transmit–receive cycle.
- **Duty cycle:** the fraction of time an instrument (or Shoalscope's sampler) is active.
- **DVM:** diel vertical migration.
- **Nv:** expected number of fish in the acoustic sampling volume of one ping.
- **Split beam:** a transducer divided into quadrants so that the echo's angle can be measured.
- **TVG:** time-varied gain, the range-dependent correction 20 log R or 40 log R.

## References

- Blackman, S. S. (1986). *Multiple-Target Tracking with Radar Applications.* Artech House.
- Clay, C. S., & Horne, J. K. (1994). Acoustic models of fish: the Atlantic cod (*Gadus
  morhua*). *Journal of the Acoustical Society of America* 96(3), 1661–1668.
- Coetzee, J. (2000). Use of a shoal analysis and patch estimation system (SHAPES) to
  characterise sardine schools. *Aquatic Living Resources* 13(1), 1–10.
- De Robertis, A., & Higginbottom, I. (2007). A post-processing technique to estimate the
  signal-to-noise ratio and remove echosounder background noise. *ICES Journal of Marine
  Science* 64(6), 1282–1291.
- Demer, D. A., et al. (2015). *Calibration of acoustic instruments.* ICES Cooperative Research
  Report No. 326.
- Faran, J. J. (1951). Sound scattering by solid cylinders and spheres. *Journal of the
  Acoustical Society of America* 23(4), 405–418.
- Foote, K. G. (1987). Fish target strengths for use in echo integrator surveys. *Journal of
  the Acoustical Society of America* 82(3), 981–987.
- Foote, K. G., Knudsen, H. P., Vestnes, G., MacLennan, D. N., & Simmonds, E. J. (1987).
  *Calibration of acoustic instruments for fish density estimation: a practical guide.* ICES
  Cooperative Research Report No. 144.
- Francois, R. E., & Garrison, G. R. (1982). Sound absorption based on ocean measurements.
  Part I and Part II. *Journal of the Acoustical Society of America* 72(3), 896–907 and 72(6),
  1879–1890.
- Gauthier, S., & Rose, G. A. (2001). Diagnostic tools for unbiased in situ target strength
  estimation. *Canadian Journal of Fisheries and Aquatic Sciences* 58(11), 2149–2155.
- Handegard, N. O., Patel, R., & Hjellvik, V. (2005). Tracking individual fish from a moving
  platform using a split-beam transducer. *Journal of the Acoustical Society of America*
  118(4), 2210–2223.
- Henderson, M. J., & Horne, J. K. (2007). Comparison of in situ, ex situ, and backscatter
  model estimates of Pacific hake (*Merluccius productus*) target strength. *Canadian Journal
  of Fisheries and Aquatic Sciences* 64(12), 1781–1794.
- IOC, SCOR & IAPSO (2010). *The international thermodynamic equation of seawater – 2010
  (TEOS-10).* Manuals and Guides 56, UNESCO.
- Jech, J. M., et al. (2015). Comparisons among ten models of acoustic backscattering used in
  aquatic ecosystem research. *Journal of the Acoustical Society of America* 138(6), 3742–3764.
- Korneliussen, R. J., & Ona, E. (2003). Synthetic echograms generated from the relative
  frequency response. *ICES Journal of Marine Science* 60(3), 636–640.
- Love, R. H. (1971). Measurements of fish target strength: a review. *Fishery Bulletin*
  69(4), 703–715.
- Macaulay, G., & Peña, H. (eds.) (2018). *The SONAR-netCDF4 convention for sonar data,
  Version 1.0.* ICES Cooperative Research Report No. 341. doi:10.17895/ices.pub.4392.
- Mackenzie, K. V. (1981). Nine-term equation for sound speed in the oceans. *Journal of the
  Acoustical Society of America* 70(3), 807–812.
- MacLennan, D. N. (1981). *The theory of solid spheres as sonar calibration targets.*
  Scottish Fisheries Research Report No. 22.
- MacLennan, D. N., Fernandes, P. G., & Dalen, J. (2002). A consistent approach to definitions
  and symbols in fisheries acoustics. *ICES Journal of Marine Science* 59(2), 365–369.
- Medwin, H., & Clay, C. S. (1998). *Fundamentals of Acoustical Oceanography.* Academic Press.
- Meeus, J. (1998). *Astronomical Algorithms*, 2nd edn. Willmann-Bell.
- Ona, E. (ed.) (1999). *Methodology for target strength measurements.* ICES Cooperative
  Research Report No. 235.
- Ona, E., & Mitson, R. B. (1996). Acoustic sampling and signal processing near the seabed:
  the deadzone revisited. *ICES Journal of Marine Science* 53(4), 677–690.
- Reid, D. G. (ed.) (2000). *Report on echo trace classification.* ICES Cooperative Research
  Report No. 238.
- Ryan, T. E., Downie, R. A., Kloser, R. J., & Keith, G. (2015). Reducing bias due to noise and
  attenuation in open-ocean echo integration data. *ICES Journal of Marine Science* 72(8),
  2482–2493.
- Sato, M., Benoit-Bird, K. J., Fletcher, K., Waldorf, W., & Wingard, C. Split-beam calibration
  of the OOI echosounder (80 m site, 120 kHz). Ocean Observatories Initiative technical report.
- Sawada, K., Furusawa, M., & Williamson, N. J. (1993). Conditions for the precise measurement
  of fish target strength in situ. *Journal of the Marine Acoustics Society of Japan* 20(2),
  73–79.
- Simmonds, J., & MacLennan, D. (2005). *Fisheries Acoustics: Theory and Practice*, 2nd edn.
  Blackwell Science.
- Soule, M., Barange, M., Solli, H., & Hampton, I. (1997). Performance of a new phase algorithm
  for discriminating between single and overlapping echoes in a split-beam echosounder. *ICES
  Journal of Marine Science* 54(5), 934–938.
- Staneva, V., Butala, S., Setiawan, B., & Lee, W.-J. (2024). Echodataflow: recipe-based
  fisheries acoustics workflow orchestration. *Proceedings of the 23rd Python in Science
  Conference (SciPy 2024).*
- Traynor, J. J. (1996). Target-strength measurements of walleye pollock (*Theragra
  chalcogramma*) and Pacific whiting (*Merluccius productus*). *ICES Journal of Marine
  Science* 53(2), 253–258.
- Urmy, S. S., Horne, J. K., & Barbee, D. H. (2012). Measuring the vertical distributional
  variability of pelagic fauna in Monterey Bay. *ICES Journal of Marine Science* 69(2),
  184–196.
- Weill, A., Scalabrin, C., & Diner, N. (1993). MOVIES-B: an acoustic detection description
  software. Application to shoal species' classification. *Aquatic Living Resources* 6(3),
  255–267.
