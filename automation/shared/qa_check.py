#!/usr/bin/env python3
"""Run baseline QA checks on captured artefacts."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from rich.console import Console
from rich.table import Table

console = Console()

WORKSPACE = Path(__file__).resolve().parents[2]
CAPTURE_ROOT = WORKSPACE / "captures"
REPORT_ROOT = WORKSPACE / "reports"


def load_summary(platform: str) -> dict:
    summary_path = REPORT_ROOT / platform / "ui-run.json"
    if not summary_path.exists():
        console.print(f"[yellow]{summary_path} missing")
        return {}
    return json.loads(summary_path.read_text(encoding="utf-8"))


def check_flows(summary: dict) -> tuple[int, int]:
    flows = summary.get("flows", []) if summary else []
    failed = [flow for flow in flows if flow.get("status") != "passed"]
    return len(flows), len(failed)


def check_layout(summary_path: Path) -> int:
    if not summary_path.exists():
        return 0
    data = json.loads(summary_path.read_text(encoding="utf-8"))
    screens = data.get("screens", {})
    return len(screens)


def check_network(platform: str) -> int:
    summary_path = REPORT_ROOT / platform / "network-summary.json"
    if not summary_path.exists():
        return 0
    data = json.loads(summary_path.read_text(encoding="utf-8"))
    return len(data.get("endpoints", {}))


def qa_platform(platform: str) -> dict:
    ui_summary = load_summary(platform)
    flow_count, failed = check_flows(ui_summary)
    layout_count = check_layout(REPORT_ROOT / platform / "layout-summary.json")
    endpoint_count = check_network(platform)

    table = Table(title=f"QA Checks ({platform})")
    table.add_column("Check")
    table.add_column("Result")

    table.add_row("Flows captured", str(flow_count))
    table.add_row("Failed flows", str(failed))
    table.add_row("Screens summarised", str(layout_count))
    table.add_row("Endpoints captured", str(endpoint_count))

    console.print(table)

    status = "passed"
    messages = []
    if flow_count == 0:
        status = "failed"
        messages.append("No flows captured")
    if failed > 0:
        status = "failed"
        messages.append("One or more flows failed")
    if endpoint_count == 0:
        messages.append("No endpoints captured")

    return {
        "platform": platform,
        "flow_count": flow_count,
        "failed_flows": failed,
        "screens": layout_count,
        "endpoints": endpoint_count,
        "status": status,
        "messages": messages,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run QA checks on capture artefacts")
    parser.add_argument("platform", choices=["ios", "android", "both"], help="Platform to inspect")
    args = parser.parse_args()

    results = []
    if args.platform in ("ios", "both"):
        results.append(qa_platform("ios"))
    if args.platform in ("android", "both"):
        results.append(qa_platform("android"))

    overall = "passed" if all(r["status"] == "passed" for r in results) else "failed"
    console.print(f"[bold]{'QA passed' if overall == 'passed' else 'QA attention needed'}")


if __name__ == "__main__":
    main()
