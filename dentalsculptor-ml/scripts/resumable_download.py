"""Range-verified download with bounded reads and automatic reconnection."""

from __future__ import annotations

import argparse
import json
import socket
import time
import urllib.error
import urllib.request
from pathlib import Path


def download(url: str, destination: Path, expected_size: int, log_path: Path, retries: int = 200) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    failures = 0
    while (destination.stat().st_size if destination.exists() else 0) < expected_size:
        offset = destination.stat().st_size if destination.exists() else 0
        if offset > expected_size:
            raise ValueError(f"Partial file is larger than expected: {offset} > {expected_size}")
        request = urllib.request.Request(url, headers={"Range": f"bytes={offset}-", "User-Agent": "DentalSculptor-Research/1.0"})
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                status = getattr(response, "status", response.getcode())
                content_range = response.headers.get("Content-Range", "")
                if offset and (status != 206 or not content_range.startswith(f"bytes {offset}-")):
                    raise ValueError(f"Server refused safe resume: HTTP {status}, Content-Range={content_range!r}")
                mode = "ab" if offset else "wb"
                checkpoint = offset
                with destination.open(mode) as output:
                    while True:
                        chunk = response.read(4 * 1024 * 1024)
                        if not chunk:
                            break
                        output.write(chunk)
                        offset += len(chunk)
                        if offset - checkpoint >= 64 * 1024 * 1024:
                            with log_path.open("a", encoding="utf-8") as log:
                                log.write(json.dumps({"event": "progress", "bytes": offset, "expected": expected_size,
                                                      "percent": round(offset * 100 / expected_size, 2), "at": time.time()}) + "\n")
                            checkpoint = offset
                failures = 0
        except (TimeoutError, socket.timeout, urllib.error.URLError, ConnectionError, OSError) as error:
            failures += 1
            with log_path.open("a", encoding="utf-8") as log:
                log.write(json.dumps({"event": "reconnect", "offset": offset, "attempt": failures,
                                      "error": f"{type(error).__name__}: {error}", "at": time.time()}) + "\n")
            if failures >= retries:
                raise
            time.sleep(min(30, 2 + failures))
    if destination.stat().st_size != expected_size:
        raise ValueError(f"Download ended at {destination.stat().st_size}; expected {expected_size}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--expected-size", type=int, required=True)
    parser.add_argument("--log", type=Path, required=True)
    args = parser.parse_args()
    download(args.url, args.destination, args.expected_size, args.log)


if __name__ == "__main__":
    main()
