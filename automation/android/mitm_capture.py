#!/usr/bin/env python3
"""Summarize a mitmproxy capture for Android automation runs."""
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
ADDON = WORKSPACE / "automation" / "shared" / "mitm_summary.py"


def process_capture(capture: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "mitmdump",
        "-nr",
        str(capture),
        "-s",
        str(ADDON),
        "--set",
        f"summary_output={output}",
    ]
    subprocess.run(cmd, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize mitmproxy capture into JSON summary")
    parser.add_argument("--input", required=True, help="Path to .mitm capture file")
    parser.add_argument("--output", required=True, help="Where to write the normalized JSON")
    args = parser.parse_args()

    capture = Path(args.input)
    if not capture.exists():
        raise FileNotFoundError(f"Capture not found: {capture}")
    process_capture(capture, Path(args.output))


if __name__ == "__main__":
    main()
