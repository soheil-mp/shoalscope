# Read one ping from a 500 MB file

Shoalscope never downloads whole echosounder files
([ADR-0004](../adr/0004-small-data-by-design.md)). This tutorial shows why that works, using a
small standard-library script. You need Python 3.10 or newer and an internet connection.

## 1. Run the example

```sh
just peek
# or: python3 examples/peek_raw_window.py
```

It reads a 500 MB file from the OOI Oregon Offshore Cabled Shallow Profiler echosounder and
prints something like:

```text
index: 288 pings in the first 16 KiB; first ping at byte 12496
header: 9 datagrams, EK80 software
channels: 38 kHz, 120 kHz, 200 kHz (ES120-7CD, ES200-7CD, ES38-18DK-Split)
ping 10 at 2026-10-01 02:54:48.545072 UTC: bytes 385524-424255
  MRU0       28 bytes
  XML0      164 bytes
  XML0      296 bytes
  RAW4     1176 bytes
  RAW3    37028 bytes
transferred 67,612 bytes in total
```

## 2. What happened

The script made three HTTP range requests:

1. **The index.** The `.idx` file next to the raw file holds one 48-byte `IDX0` datagram per
   ping cycle, with the byte offset of that ping. The first 16 KiB cover 288 pings.
2. **The header.** Everything before the first ping (12,496 bytes here) is configuration:
   transceivers, transducers, frequencies and filters.
3. **One ping.** The bytes between two consecutive offsets are exactly one ping cycle: motion
   data (`MRU0`), ping parameters (`XML0`) and the samples (`RAW3`, `RAW4`).

Every Simrad datagram starts and ends with its length, so the script can check that each range
frames cleanly. That framing is also what lets Shoalscope find windows in files without an index,
by searching timestamps (roadmap item M3.11).

## 3. Try another ping

```sh
just peek --ping 1000
```

A 60-second window is about 60 such pings: roughly 2 MB of a 500 MB file. That ratio is the
basis of Shoalscope's [data budgets](../research/02-data-sources.md#7-data-budget).
