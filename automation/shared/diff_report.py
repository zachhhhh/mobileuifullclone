#!/usr/bin/env python3
"""Compute diffs between current and previous release summaries."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from rich.console import Console
from rich.table import Table

console = Console()

WORKSPACE = Path(__file__).resolve().parents[2]
DOCS = WORKSPACE / "docs"


def load(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def diff_platform(current: dict, previous: dict, platform: str) -> dict:
    cur = current.get("platforms", {}).get(platform, {})
    prev = previous.get("platforms", {}).get(platform, {})

    cur_flows = {flow.get("slug", flow.get("name")): flow for flow in cur.get("flows", [])}
    prev_flows = {flow.get("slug", flow.get("name")): flow for flow in prev.get("flows", [])}

    new_flows = sorted(set(cur_flows) - set(prev_flows))
    removed_flows = sorted(set(prev_flows) - set(cur_flows))
    failing = [slug for slug, flow in cur_flows.items() if flow.get("status") != "passed"]

    cur_endpoints = set(cur.get("endpoints", {}).keys())
    prev_endpoints = set(prev.get("endpoints", {}).keys())
    new_endpoints = sorted(cur_endpoints - prev_endpoints)
    removed_endpoints = sorted(prev_endpoints - cur_endpoints)

    return {
        "platform": platform,
        "new_flows": new_flows,
        "removed_flows": removed_flows,
        "failing_flows": failing,
        "new_endpoints": new_endpoints,
        "removed_endpoints": removed_endpoints,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Diff release summaries")
    parser.add_argument("current", default="docs/release-summary.json")
    parser.add_argument("previous", default="docs/release-summary.prev.json")
    args = parser.parse_args()

    current = load(Path(args.current))
    previous = load(Path(args.previous))

    results = []
    for platform in ("ios", "android"):
        results.append(diff_platform(current, previous, platform))

    table = Table(title="Release Diff")
    table.add_column("Platform")
    table.add_column("New flows")
    table.add_column("Removed flows")
    table.add_column("Failing")
    table.add_column("New endpoints")
    table.add_column("Removed endpoints")

    for r in results:
        table.add_row(
            r["platform"],
            str(len(r["new_flows"])),
            str(len(r["removed_flows"])),
            str(len(r["failing_flows"])),
            str(len(r["new_endpoints"])),
            str(len(r["removed_endpoints"])),
        )

    console.print(table)

    diff_path = DOCS / "release-diff.json"
    diff_path.write_text(json.dumps({"results": results}, indent=2), encoding="utf-8")
    console.print(f"Wrote diff {diff_path}")


if __name__ == "__main__":
    main()
