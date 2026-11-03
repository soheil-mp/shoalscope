# Processing levels and attributes

Module: `shoalscope_core.levels` ([ADR-0003](../adr/0003-echolevels-as-storage-layers.md)).

## Levels

| Level | Data | Storage prefix |
| :-- | :-- | :-- |
| L0 | Raw instrument bytes as recorded (read by byte range, never retained) | `l0` |
| L1A, L1B | Converted to a standard format; then quality-control flags and metadata corrections | `l1` |
| L2A, L2B | Calibrated Sv and TS; then noise and unwanted echoes removed | `l2` |
| L3A, L3B | Sv on a regular grid (MVBS); then classified into acoustic categories | `l3` |
| L4 | Biological estimates: NASC, densities, targets, tracks and schools | `l4` |

Reference data lives under `ref` and operational data under `ops`.

## Processing attributes

Every dataset carries these as Zarr group attributes, and every table write as Iceberg snapshot
properties:

| Key | Meaning |
| :-- | :-- |
| `shoalscope_level` | Echolevels level |
| `shoalscope_software_version` | Version of the package that wrote the data |
| `shoalscope_calibration_set` | Calibration values used (`file` = the values in the raw file) |
| `shoalscope_environment_profile` | Sound speed and absorption used (`file`, or `constant:c=...,alpha=...`) |
| `shoalscope_configuration_hash` | SHA-256 of the processing configuration in canonical JSON |

The L4 configuration hash includes the hash of the L2A configuration it was computed from, so a
NASC value can be traced back through every step.
