#!/usr/bin/env python3
"""Read one ping from a remote Simrad raw file with three small HTTP range requests.

This is the idea behind Shoalscope's ingestion (ADR-0004), reduced to the standard library:

1. read the first records of the ``.idx`` file, which give each ping's byte offset;
2. read the file header (everything before the first ping) and list its channels;
3. read exactly one ping cycle and list its datagrams.

It needs the file's ``.idx`` index (OOI files and NOAA EK60 cruises have one; for files
without one, Shoalscope searches datagram timestamps instead, roadmap item M3.11). It never
downloads a whole file: every request asks for a byte range and is refused unless the server
answers ``206 Partial Content``.

Usage:
    python3 examples/peek_raw_window.py [RAW_URL] [--ping N]

The default URL is a 500 MB file from the OOI Oregon Offshore Cabled Shallow Profiler echosounder
(CE04OSPS-PC01B-ZPLSCB102). Data: NSF Ocean Observatories Initiative.
"""

from __future__ import annotations

import argparse
import re
import struct
import sys
import urllib.request
from datetime import UTC, datetime, timedelta

DEFAULT_URL = (
    "https://rawdata.oceanobservatories.org/files/CE04OSPS/PC01B/ZPLSCB102/"
    "2026/10/01/ZPLSCB102-D20261001-T025438.raw"
)
USER_AGENT = "shoalscope-example/0.0 (+https://github.com/soheil-mp/shoalscope)"
NT_EPOCH = datetime(1601, 1, 1, tzinfo=UTC)
IDX0_BODY = struct.Struct("<IdddQ")  # ping number, distance, latitude, longitude, file offset
MAX_RANGE_BYTES = 1 << 20  # refuse any single request larger than 1 MiB


class Fetcher:
    """HTTP range reader that counts bytes and refuses full downloads."""

    def __init__(self) -> None:
        """Start with no bytes read."""
        self.bytes_read = 0

    def get(self, url: str, start: int, end: int) -> bytes:
        """Return bytes ``start..end`` (inclusive) of ``url``."""
        if not url.startswith("https://"):
            msg = f"only https URLs are allowed: {url}"
            raise ValueError(msg)
        if end - start + 1 > MAX_RANGE_BYTES:
            msg = f"refusing a {end - start + 1}-byte request"
            raise ValueError(msg)
        request = urllib.request.Request(  # noqa: S310 - scheme checked above
            url, headers={"Range": f"bytes={start}-{end}", "User-Agent": USER_AGENT}
        )
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310 - scheme checked above
            if response.status != 206:
                msg = f"server ignored the range request (HTTP {response.status})"
                raise RuntimeError(msg)
            data: bytes = response.read(end - start + 1)
        self.bytes_read += len(data)
        return data


def datagrams(buf: bytes) -> list[tuple[str, int, datetime, bytes]]:
    """Split a buffer into complete datagrams: (type, length, time, body)."""
    out = []
    pos = 0
    while pos + 4 <= len(buf):
        (length,) = struct.unpack_from("<i", buf, pos)
        if length < 12 or pos + 4 + length + 4 > len(buf):
            break  # incomplete datagram at the end of the range
        (trailer,) = struct.unpack_from("<i", buf, pos + 4 + length)
        if trailer != length:
            msg = f"framing error at byte {pos}: {length} != {trailer}"
            raise ValueError(msg)
        kind = buf[pos + 4 : pos + 8].decode("ascii", "replace")
        low, high = struct.unpack_from("<II", buf, pos + 8)
        when = NT_EPOCH + timedelta(microseconds=((high << 32) | low) / 10)
        out.append((kind, length, when, buf[pos + 16 : pos + 4 + length]))
        pos += 4 + length + 4
    return out


def main() -> int:
    """Run the three range requests and print what they contain."""
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("url", nargs="?", default=DEFAULT_URL, help="URL of a .raw file")
    parser.add_argument("--ping", type=int, default=10, help="index of the ping cycle to read")
    args = parser.parse_args()
    fetch = Fetcher()

    # 1. Index: one 48-byte IDX0 datagram per ping cycle, after a small XML0 header.
    index = datagrams(fetch.get(args.url.removesuffix(".raw") + ".idx", 0, 16 * 1024 - 1))
    pings = [(t, IDX0_BODY.unpack(body)) for kind, _, t, body in index if kind == "IDX0"]
    if len(pings) <= args.ping + 1:
        print(f"only {len(pings)} index records in the first 16 KiB", file=sys.stderr)
        return 1
    first_offset = pings[0][1][4]
    start, end = pings[args.ping][1][4], pings[args.ping + 1][1][4] - 1
    print(f"index: {len(pings)} pings in the first 16 KiB; first ping at byte {first_offset}")

    # 2. Header: configuration datagrams before the first ping.
    header = datagrams(fetch.get(args.url, 0, first_offset - 1))
    config = next(body for kind, _, _, body in header if kind == "XML0").decode("utf-8", "replace")
    freqs = sorted({int(f) for f in re.findall(r'Frequency="(\d+)"', config) if int(f) < 1_000_000})
    names = sorted(set(re.findall(r'TransducerName="([^"]+)"', config)))
    app = re.search(r'ApplicationName="([^"]+)"', config)
    print(f"header: {len(header)} datagrams, {app.group(1) if app else '?'} software")
    print(f"channels: {', '.join(f'{f // 1000} kHz' for f in freqs)} ({', '.join(names)})")

    # 3. One ping cycle, exactly as the index describes it.
    when = pings[args.ping][0]
    print(f"ping {args.ping} at {when:%Y-%m-%d %H:%M:%S.%f} UTC: bytes {start}-{end}")
    for kind, length, _, _ in datagrams(fetch.get(args.url, start, end)):
        print(f"  {kind}  {length:>7} bytes")

    print(f"transferred {fetch.bytes_read:,} bytes in total")
    return 0


if __name__ == "__main__":
    sys.exit(main())
