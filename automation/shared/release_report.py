#!/usr/bin/env python3
"""Generate release report summarizing latest clone sync."""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from rich.console import Console

console = Console()

WORKSPACE = Path(__file__).resolve().parents[2]
CAPTURE_ROOT = WORKSPACE / "captures"
REPORT_ROOT = WORKSPACE / "reports"
RELEASE_ROOT = WORKSPACE / "docs"


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def generate(platform: str) -> dict:
    ui_summary = load_json(REPORT_ROOT / platform / "ui-run.json")
    layout = load_json(REPORT_ROOT / platform / "layout-summary.json")
    assets = load_json(REPORT_ROOT / platform / "assets-summary.json")
    network = load_json(REPORT_ROOT / platform / "network-summary.json")
    security = load_json(REPORT_ROOT / platform / "security-audit.json")

    info = {
        "platform": platform,
        "run_id": ui_summary.get("runId") or layout.get("run_id"),
        "flows": ui_summary.get("flows", []),
        "screens": layout.get("screens", {}),
        "assets": assets.get("categories", {}),
        "endpoints": network.get("endpoints", {}),
        "security": security,
    }
    return info


def write_report(data: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    console.print(f"Wrote release report {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate release summary")
    parser.add_argument("platform", choices=["ios", "android", "both"], help="Platform to include")
    args = parser.parse_args()

    snapshot = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "platforms": {},
    }

    if args.platform in ("ios", "both"):
        snapshot["platforms"]["ios"] = generate("ios")
    if args.platform in ("android", "both"):
        snapshot["platforms"]["android"] = generate("android")

    write_report(snapshot, RELEASE_ROOT / "release-summary.json")


if __name__ == "__main__":
    main()
