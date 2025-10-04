#!/usr/bin/env python3
"""Diff captured artefacts between runs to highlight UI/network/asset drift."""
from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from rich.console import Console

console = Console()

WORKSPACE = Path(__file__).resolve().parents[2]
REPORT_ROOT = WORKSPACE / "reports"
DESIGN_ROOT = WORKSPACE / "design-tokens"


@dataclass
class FilePair:
    current: Path
    previous: Path | None
    description: str


def load_json(path: Path | None) -> dict[str, Any]:
    if not path or not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        console.print(f"[yellow]Unable to parse JSON from {path}")
        return {}


def resolve_previous(path: Path, provided: Path | None = None, root: Path | None = None) -> Path | None:
    if provided:
        return provided
    if root:
        candidate = root / path.name
        if candidate.exists():
            return candidate
    prev_candidate = path.with_suffix(path.suffix.replace(".json", ".prev.json"))
    if prev_candidate.exists():
        return prev_candidate
    baseline_candidate = path.with_suffix(path.suffix.replace(".json", ".baseline.json"))
    if baseline_candidate.exists():
        return baseline_candidate
    return None


def diff_network(current: dict[str, Any], previous: dict[str, Any]) -> dict[str, Any]:
    current_endpoints = current.get("endpoints", {}) or {}
    previous_endpoints = previous.get("endpoints", {}) or {}
    current_keys = set(current_endpoints.keys())
    previous_keys = set(previous_endpoints.keys())

    added = []
    for key in sorted(current_keys - previous_keys):
        entry = current_endpoints[key]
        added.append({
            "endpoint": key,
            "hosts": entry.get("hosts", []),
            "status_codes": entry.get("status_codes", {}),
        })

    removed = []
    for key in sorted(previous_keys - current_keys):
        entry = previous_endpoints[key]
        removed.append({
            "endpoint": key,
            "hosts": entry.get("hosts", []),
            "status_codes": entry.get("status_codes", {}),
        })

    changed = []
    shared = current_keys & previous_keys
    for key in sorted(shared):
        current_entry = current_endpoints.get(key, {})
        previous_entry = previous_endpoints.get(key, {})
        delta: dict[str, Any] = {}
        for field in ("hosts", "status_codes"):
            if current_entry.get(field) != previous_entry.get(field):
                delta[field] = {
                    "before": previous_entry.get(field),
                    "after": current_entry.get(field),
                }
        if delta:
            changed.append({"endpoint": key, "changes": delta})

    return {
        "added": added,
        "removed": removed,
        "changed": changed,
        "totals": {
            "added": len(added),
            "removed": len(removed),
            "changed": len(changed),
            "current": len(current_endpoints),
            "previous": len(previous_endpoints),
        },
    }


def diff_assets(current: dict[str, Any], previous: dict[str, Any]) -> dict[str, Any]:
    current_categories = current.get("categories", {}) or {}
    previous_categories = previous.get("categories", {}) or {}
    current_keys = set(current_categories.keys())
    previous_keys = set(previous_categories.keys())

    added = []
    for key in sorted(current_keys - previous_keys):
        entry = current_categories[key]
        added.append({
            "category": key,
            "count": entry.get("count", 0),
            "bytes": entry.get("bytes", 0),
        })

    removed = []
    for key in sorted(previous_keys - current_keys):
        entry = previous_categories[key]
        removed.append({
            "category": key,
            "count": entry.get("count", 0),
            "bytes": entry.get("bytes", 0),
        })

    changed = []
    for key in sorted(current_keys & previous_keys):
        current_entry = current_categories.get(key, {})
        previous_entry = previous_categories.get(key, {})
        if (
            current_entry.get("count") != previous_entry.get("count")
            or current_entry.get("bytes") != previous_entry.get("bytes")
        ):
            changed.append({
                "category": key,
                "before": previous_entry,
                "after": current_entry,
            })

    totals_current = current.get("totals", {})
    totals_previous = previous.get("totals", {})
    return {
        "added": added,
        "removed": removed,
        "changed": changed,
        "totals": {
            "current": totals_current,
            "previous": totals_previous,
        },
    }


def diff_tokens(current: dict[str, Any], previous: dict[str, Any]) -> dict[str, Any]:
    current_screens = current.get("screens", {}) or {}
    previous_screens = previous.get("screens", {}) or {}
    current_keys = set(current_screens.keys())
    previous_keys = set(previous_screens.keys())

    added = sorted(current_keys - previous_keys)
    removed = sorted(previous_keys - current_keys)
    changed = []
    for key in sorted(current_keys & previous_keys):
        current_entry = current_screens.get(key, {})
        previous_entry = previous_screens.get(key, {})
        metrics_delta = current_entry.get("metrics") != previous_entry.get("metrics")
        status_delta = current_entry.get("status") != previous_entry.get("status")
        if metrics_delta or status_delta:
            changed.append({
                "screen": key,
                "metrics_changed": metrics_delta,
                "status_before": previous_entry.get("status"),
                "status_after": current_entry.get("status"),
            })

    return {
        "added": added,
        "removed": removed,
        "changed": changed,
        "totals": {
            "current": len(current_screens),
            "previous": len(previous_screens),
        },
    }


def risk_rating(diff_payload: dict[str, Any]) -> dict[str, Any]:
    counts = []
    for section in ("network", "assets", "tokens"):
        section_data = diff_payload.get(section, {})
        if not isinstance(section_data, dict):
            continue
        totals = section_data.get("totals", {})
        if section == "assets":
            current_total = totals.get("current", {}).get("files", 0)
            previous_total = totals.get("previous", {}).get("files", 0)
            delta = abs(current_total - previous_total)
        else:
            delta = (
                totals.get("added", 0)
                + totals.get("removed", 0)
                + totals.get("changed", 0)
            )
        counts.append(delta)
    aggregate = sum(counts)
    if aggregate == 0:
        level = "low"
        label = "stable"
    elif aggregate <= 5:
        level = "medium"
        label = "review"
    else:
        level = "high"
        label = "attention"
    return {"level": level, "label": label, "score": aggregate}


def format_markdown(platform: str, diff_payload: dict[str, Any]) -> str:
    network = diff_payload.get("network", {})
    assets = diff_payload.get("assets", {})
    tokens = diff_payload.get("tokens", {})
    risk = diff_payload.get("risk", {})

    lines = [f"# {platform.upper()} Diff Summary", ""]
    if risk:
        lines.append(f"- Risk: **{risk.get('label', 'n/a')}** (score {risk.get('score', 0)})")
    if network:
        totals = network.get("totals", {})
        lines.extend(
            [
                "## Network",
                f"- Added: {totals.get('added', 0)}",
                f"- Removed: {totals.get('removed', 0)}",
                f"- Changed: {totals.get('changed', 0)}",
            ]
        )
        for item in network.get("added", [])[:5]:
            lines.append(f"  - ➕ {item['endpoint']}")
        for item in network.get("removed", [])[:5]:
            lines.append(f"  - ➖ {item['endpoint']}")
    if assets:
        totals = assets.get("totals", {})
        lines.extend(
            [
                "## Assets",
                f"- Current files: {totals.get('current', {}).get('files', 0)}",
                f"- Previous files: {totals.get('previous', {}).get('files', 0)}",
            ]
        )
        for item in assets.get("changed", [])[:5]:
            lines.append(
                f"  - ∆ {item['category']}: {item['before'].get('count', 0)} → {item['after'].get('count', 0)}"
            )
    if tokens:
        totals = tokens.get("totals", {})
        lines.extend(
            [
                "## Design Tokens",
                f"- Screens tracked: {totals.get('current', 0)}",
                f"- Added screens: {len(tokens.get('added', []))}",
                f"- Removed screens: {len(tokens.get('removed', []))}",
            ]
        )
        for screen in tokens.get("added", [])[:5]:
            lines.append(f"  - ➕ {screen}")
        for screen in tokens.get("removed", [])[:5]:
            lines.append(f"  - ➖ {screen}")
    return "\n".join(lines).strip() + "\n"


def process_platform(
    platform: str,
    previous_root: Path | None,
    output_dir: Path | None,
    store_baseline: bool,
) -> dict[str, Any]:
    report_dir = REPORT_ROOT / platform
    tokens_path = DESIGN_ROOT / platform / "tokens.json"

    file_pairs = [
        FilePair(
            current=report_dir / "network-summary.json",
            previous=resolve_previous(report_dir / "network-summary.json", root=previous_root),
            description="network",
        ),
        FilePair(
            current=report_dir / "assets-summary.json",
            previous=resolve_previous(report_dir / "assets-summary.json", root=previous_root),
            description="assets",
        ),
        FilePair(
            current=tokens_path,
            previous=resolve_previous(tokens_path, root=previous_root),
            description="tokens",
        ),
    ]

    payload: dict[str, Any] = {
        "platform": platform,
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }

    for pair in file_pairs:
        current_data = load_json(pair.current)
        previous_data = load_json(pair.previous)
        if pair.description == "network":
            payload["network"] = diff_network(current_data, previous_data)
        elif pair.description == "assets":
            payload["assets"] = diff_assets(current_data, previous_data)
        else:
            payload["tokens"] = diff_tokens(current_data, previous_data)

    payload["risk"] = risk_rating(payload)

    target_dir = output_dir or report_dir
    target_dir.mkdir(parents=True, exist_ok=True)
    json_path = target_dir / "diff-summary.json"
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    console.print(f"Wrote diff summary to {json_path}")

    markdown = format_markdown(platform, payload)
    markdown_path = target_dir / "diff-summary.md"
    markdown_path.write_text(markdown, encoding="utf-8")
    console.print(f"Wrote diff summary markdown to {markdown_path}")

    if store_baseline:
        for pair in file_pairs:
            if not pair.current.exists():
                continue
            baseline_path = pair.current.with_suffix(pair.current.suffix.replace(".json", ".prev.json"))
            baseline_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(pair.current, baseline_path)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Diff artefacts between automation runs")
    parser.add_argument("platform", choices=["ios", "android", "both"], help="Platform to process")
    parser.add_argument(
        "--previous-root",
        type=Path,
        help="Optional root directory containing baseline reports organised by platform",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Directory to write diff outputs. Defaults to reports/<platform>",
    )
    parser.add_argument(
        "--store-baseline",
        action="store_true",
        help="Copy current summaries to *.prev.json after diff completes",
    )
    args = parser.parse_args()

    results = []
    platforms = [args.platform] if args.platform != "both" else ["ios", "android"]
    for platform in platforms:
        results.append(
            process_platform(
                platform,
                previous_root=args.previous_root / platform if args.previous_root else None,
                output_dir=args.output_dir / platform if args.output_dir else None,
                store_baseline=args.store_baseline,
            )
        )

    if len(results) == 2:
        total_score = sum(item.get("risk", {}).get("score", 0) for item in results)
        console.print(f"Aggregate diff score: {total_score}")


if __name__ == "__main__":
    main()
