# shoalscope-proc

Acoustic processing L1 to L4: calibration, cleaning, targets, tracks, echo integration.

Part of [Shoalscope](../../README.md). Planned work for this package is in
[ROADMAP.md](../../ROADMAP.md).

## Modules

| Module | What it does |
| :-- | :-- |
| `shoalscope_proc.l2a` | L0 → L2A: open an EK80 file with echopype, compute CW Sv with the file's calibration values, write each window as one commit to an Icechunk repository (`l2a/sv/<window_id>`, with the source file's SHA-256) |
| `shoalscope_proc.integration` | L3 MVBS on a fixed grid (`echopype.commongrid`, linear averaging) and L4 NASC per time cell for a stationary echosounder (MacLennan et al., 2002) |
