#!/usr/bin/env python3
"""Summarize mitmproxy capture files into endpoint inventories and OpenAPI skeleton."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlparse

from rich.console import Console

console = Console()

WORKSPACE = Path(__file__).resolve().parents[2]
CAPTURE_ROOT = WORKSPACE / "captures"
REPORT_ROOT = WORKSPACE / "reports"
FIXTURE_ROOT = WORKSPACE / "fixtures" / "shared"
MITM_SUMMARY_SCRIPT = WORKSPACE / "automation" / "shared" / "mitm_summary.py"


def run_mitm_summary(mitm_file: Path, output_json: Path) -> bool:
    try:
        cmd = [
            "mitmdump",
            "-nr",
            str(mitm_file),
            "-s",
            str(MITM_SUMMARY_SCRIPT),
            "--set",
            f"summary_output={output_json}",
        ]
        console.log("$ " + " ".join(cmd))
        subprocess.run(cmd, check=True)
        return True
    except FileNotFoundError:
        console.print("[bold red]mitmdump not available; install mitmproxy on capture host")
        return False
    except subprocess.CalledProcessError as err:
        console.print(f"[bold red]Failed to summarize {mitm_file}: {err}")
        return False


def aggregate_summary(files: list[Path]) -> dict[str, dict]:
    endpoints: dict[str, dict] = {}

    for summary_file in files:
        try:
            data = json.loads(summary_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as err:
            console.print(f"[yellow]Skipping invalid JSON {summary_file}: {err}")
            continue

        for record in data:
            method = record.get("method", "GET")
            url = record.get("url", "")
            parsed = urlparse(url)
            path = parsed.path or record.get("path") or "/"
            key = f"{method} {path}"
            entry = endpoints.setdefault(
                key,
                {
                    "method": method,
                    "path": path,
                    "hosts": set(),
                    "examples": [],
                    "status_codes": defaultdict(int),
                },
            )

            if parsed.netloc:
                entry["hosts"].add(parsed.netloc)
            if record.get("host"):
                entry["hosts"].add(record["host"])

            status = record.get("status_code")
            if status is not None:
                entry["status_codes"][status] += 1

            example = {
                "url": url,
                "status_code": status,
                "reason": record.get("reason"),
                "request_headers": record.get("request_headers"),
                "response_headers": record.get("response_headers"),
                "request_body": record.get("request_body"),
                "response_body": record.get("response_body"),
            }
            entry["examples"].append(example)

    # normalise sets and defaultdicts
    normalised: dict[str, dict] = {}
    for key, entry in endpoints.items():
        normalised[key] = {
            "method": entry["method"],
            "path": entry["path"],
            "hosts": sorted(entry["hosts"]),
            "status_codes": dict(entry["status_codes"]),
            "examples": entry["examples"][:5],  # limit examples for brevity
        }
    return normalised


def write_openapi(endpoints: dict[str, dict], output: Path) -> None:
    paths: dict[str, dict] = {}
    for endpoint in endpoints.values():
        path = endpoint["path"]
        method = endpoint["method"].lower()
        path_item = paths.setdefault(path, {})
        responses = {
            str(code): {
                "description": "Captured response",
            }
            for code in endpoint["status_codes"].keys()
        } or {"default": {"description": "Captured response"}}
        path_item[method] = {
            "summary": f"Captured {endpoint['method']} {path}",
            "responses": responses,
        }

    openapi_doc = {
        "openapi": "3.0.0",
        "info": {
            "title": "Captured API",
            "version": "0.1.0",
        },
        "paths": paths,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(openapi_doc, indent=2), encoding="utf-8")


def summarise_platform(platform: str) -> None:
    network_dir = CAPTURE_ROOT / platform / "network"
    if not network_dir.exists():
        console.print(f"[yellow]No network captures for {platform}")
        return

    report_dir = REPORT_ROOT / platform
    report_dir.mkdir(parents=True, exist_ok=True)
    per_flow_dir = report_dir / "network"
    per_flow_dir.mkdir(parents=True, exist_ok=True)

    summary_files: list[Path] = []
    for mitm_file in sorted(network_dir.glob("*.mitm")):
        output_json = per_flow_dir / f"{mitm_file.stem}.json"
        if run_mitm_summary(mitm_file, output_json):
            summary_files.append(output_json)

    if not summary_files:
        console.print(f"[yellow]No summaries generated for {platform}")
        return

    aggregated = aggregate_summary(summary_files)
    summary_output = report_dir / "network-summary.json"
    summary_output.write_text(json.dumps({"endpoints": aggregated}, indent=2), encoding="utf-8")
    console.print(f"Wrote aggregated network summary to {summary_output}")

    openapi_output = FIXTURE_ROOT / f"api-{platform}.json"
    write_openapi(aggregated, openapi_output)
    console.print(f"Wrote OpenAPI skeleton to {openapi_output}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize mitmproxy network captures")
    parser.add_argument("platform", choices=["ios", "android", "both"], help="Platform to process")
    args = parser.parse_args()

    if args.platform in ("ios", "both"):
        summarise_platform("ios")
    if args.platform in ("android", "both"):
        summarise_platform("android")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(1)
