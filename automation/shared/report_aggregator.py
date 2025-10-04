#!/usr/bin/env python3
"""Aggregate automation outputs into a daily summary report."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from rich.console import Console

console = Console()

WORKSPACE = Path(__file__).resolve().parents[2]
REPORT_ROOT = WORKSPACE / "reports"
RELEASE_SUMMARY = WORKSPACE / "docs" / "release-summary.json"
SUMMARY_MD = REPORT_ROOT / "daily-summary.md"
SUMMARY_JSON = REPORT_ROOT / "daily-summary.json"


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        console.print(f"[yellow]Unable to parse JSON from {path}")
        return {}


def git_commit() -> str:
    env_commit = os.getenv("GITHUB_SHA") or os.getenv("CI_COMMIT_SHA")
    if env_commit:
        return env_commit
    try:
        result = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=WORKSPACE)
        return result.decode("utf-8").strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def locate_latest_binary(platform: str) -> str | None:
    binary_dir = WORKSPACE / "captures" / platform / "binaries"
    if not binary_dir.exists():
        return None

    candidates: list[Path] = []
    for pattern in ("*.ipa", "*.apk", "*.aab"):
        candidates.extend(binary_dir.rglob(pattern))

    if not candidates:
        # fall back to most recent directory name for visibility
        latest_dir = sorted(binary_dir.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
        return latest_dir[0].name if latest_dir else None

    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return str(candidates[0].relative_to(WORKSPACE))


def summarise_flows(ui_summary: dict[str, Any]) -> dict[str, Any]:
    flows = ui_summary.get("flows", []) if isinstance(ui_summary, dict) else []
    total = len(flows)
    succeeded = sum(1 for flow in flows if flow.get("status") in {"passed", "completed", "success"})
    failed = [flow for flow in flows if flow.get("status") not in {"passed", "completed", "success"}]
    return {
        "total": total,
        "succeeded": succeeded,
        "failed": [
            {
                "name": flow.get("name") or flow.get("slug") or "unknown",
                "status": flow.get("status"),
                "error": flow.get("error"),
            }
            for flow in failed
        ],
    }


def summarise_platform(platform: str) -> dict[str, Any]:
    report_dir = REPORT_ROOT / platform
    ui_summary = load_json(report_dir / "ui-run.json")
    network_summary = load_json(report_dir / "network-summary.json")
    assets_summary = load_json(report_dir / "assets-summary.json")
    diff_summary = load_json(report_dir / "diff-summary.json")
    release_data = load_json(RELEASE_SUMMARY).get("platforms", {}).get(platform, {})

    endpoints = network_summary.get("endpoints", {}) if isinstance(network_summary, dict) else {}
    assets_totals = assets_summary.get("totals", {}) if isinstance(assets_summary, dict) else {}
    diff_risk = diff_summary.get("risk", {}) if isinstance(diff_summary, dict) else {}

    summary = {
        "platform": platform,
        "run_id": release_data.get("run_id") or ui_summary.get("runId"),
        "binary": locate_latest_binary(platform),
        "flows": summarise_flows(ui_summary),
        "network": {
            "endpoint_count": len(endpoints),
            "notable_additions": [item.get("endpoint") for item in diff_summary.get("network", {}).get("added", [])[:5]],
            "notable_removals": [item.get("endpoint") for item in diff_summary.get("network", {}).get("removed", [])[:5]],
        },
        "assets": {
            "files": assets_totals.get("files"),
            "bytes": assets_totals.get("bytes"),
            "changed_categories": [item.get("category") for item in diff_summary.get("assets", {}).get("changed", [])[:5]],
        },
        "tokens": {
            "screens": diff_summary.get("tokens", {}).get("totals", {}).get("current"),
            "added": diff_summary.get("tokens", {}).get("added", [])[:5],
            "removed": diff_summary.get("tokens", {}).get("removed", [])[:5],
        },
        "risk": diff_risk,
    }
    if summary["flows"]["total"] == 0 and summary["network"]["endpoint_count"] == 0:
        summary["note"] = "No capture data available"
    return summary


def format_size(num: int | None) -> str:
    if not num:
        return "0"
    if num < 1024:
        return f"{num} B"
    units = ["KB", "MB", "GB", "TB"]
    value = float(num)
    for unit in units:
        value /= 1024
        if value < 1024:
            return f"{value:.2f} {unit}"
    return f"{value:.2f} PB"


def render_markdown(metadata: dict[str, Any], platforms: list[dict[str, Any]]) -> str:
    lines = ["# Daily Automation Summary", ""]
    lines.append(f"- Generated at: {metadata['generated_at']}")
    lines.append(f"- Commit: `{metadata['commit']}`")
    if metadata.get("run_id"):
        lines.append(f"- Run ID: {metadata['run_id']}")
    if metadata.get("tool_versions"):
        versions = ", ".join(f"{k}: {v}" for k, v in metadata["tool_versions"].items())
        lines.append(f"- Tooling: {versions}")
    lines.append("")

    if not platforms:
        lines.append("No platform reports available.")
        return "\n".join(lines) + "\n"

    for platform in platforms:
        lines.append(f"## {platform['platform'].upper()}")
        lines.append("")
        if platform.get("run_id"):
            lines.append(f"- Run ID: `{platform['run_id']}`")
        if platform.get("binary"):
            lines.append(f"- Latest binary: {platform['binary']}")
        flow_stats = platform.get("flows", {})
        lines.append(
            f"- Flows: {flow_stats.get('succeeded', 0)}/{flow_stats.get('total', 0)} passed"
        )
        failed = flow_stats.get("failed", [])
        if failed:
            lines.append("  - ❌ Failures:")
            for flow in failed:
                name = flow.get("name") or "unknown"
                status = flow.get("status") or "failure"
                lines.append(f"    - {name} ({status})")
        network = platform.get("network", {})
        lines.append(f"- Network endpoints captured: {network.get('endpoint_count', 0)}")
        additions = [item for item in network.get("notable_additions", []) if item]
        removals = [item for item in network.get("notable_removals", []) if item]
        if additions:
            lines.append("  - ➕ New endpoints:")
            for endpoint in additions:
                lines.append(f"    - {endpoint}")
        if removals:
            lines.append("  - ➖ Removed endpoints:")
            for endpoint in removals:
                lines.append(f"    - {endpoint}")
        assets = platform.get("assets", {})
        lines.append(
            f"- Assets mirrored: {assets.get('files', 0)} files ({format_size(assets.get('bytes'))})"
        )
        if assets.get("changed_categories"):
            lines.append("  - ∆ Categories: " + ", ".join(assets["changed_categories"]))
        tokens = platform.get("tokens", {})
        if tokens.get("screens") is not None:
            lines.append(
                f"- Design tokens: {tokens.get('screens', 0)} screens tracked"
            )
        if tokens.get("added"):
            lines.append("  - ➕ Screens: " + ", ".join(tokens["added"]))
        if tokens.get("removed"):
            lines.append("  - ➖ Screens: " + ", ".join(tokens["removed"]))
        risk = platform.get("risk", {})
        if risk:
            lines.append(
                f"- Risk level: {risk.get('label', 'unknown')} (score {risk.get('score', 0)})"
            )
        if platform.get("note"):
            lines.append(f"- Note: {platform['note']}")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def gather_metadata() -> dict[str, Any]:
    generated_at = datetime.utcnow().isoformat() + "Z"
    run_id = os.getenv("GITHUB_RUN_ID") or os.getenv("CI_PIPELINE_ID")
    tool_versions: dict[str, str] = {}
    if os.getenv("APPIUM_VERSION"):
        tool_versions["appium"] = os.getenv("APPIUM_VERSION")
    if os.getenv("MITMPROXY_VERSION"):
        tool_versions["mitmproxy"] = os.getenv("MITMPROXY_VERSION")
    metadata = {
        "generated_at": generated_at,
        "commit": git_commit(),
        "run_id": run_id,
    }
    if tool_versions:
        metadata["tool_versions"] = tool_versions
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description="Aggregate reports into a summary")
    parser.add_argument(
        "--platforms",
        nargs="*",
        choices=["ios", "android"],
        help="Subset of platforms to include. Defaults to all detected.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Override markdown output path.",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        help="Optional JSON output location.",
    )
    args = parser.parse_args()

    platforms_to_process = args.platforms
    if not platforms_to_process:
        platforms_to_process = [p for p in ("ios", "android") if (REPORT_ROOT / p).exists()]

    summaries = []
    for platform in platforms_to_process:
        summary = summarise_platform(platform)
        if summary["flows"]["total"] == 0 and summary["network"]["endpoint_count"] == 0:
            console.print(f"[yellow]No capture artefacts detected for {platform}; including placeholder summary")
        summaries.append(summary)

    metadata = gather_metadata()
    markdown = render_markdown(metadata, summaries)
    output_path = args.output or SUMMARY_MD
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")
    console.print(f"Wrote markdown summary to {output_path}")

    json_payload = {
        "metadata": metadata,
        "platforms": summaries,
    }
    json_path = args.json_output or SUMMARY_JSON
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(json_payload, indent=2), encoding="utf-8")
    console.print(f"Wrote JSON summary to {json_path}")


if __name__ == "__main__":
    main()
