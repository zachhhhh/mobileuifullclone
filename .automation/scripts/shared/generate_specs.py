#!/usr/bin/env python3
"""Generate design tokens and API specs from captured artefacts."""
from __future__ import annotations

import json
from pathlib import Path

import yaml
from rich.console import Console

console = Console()

WORKSPACE = Path(__file__).resolve().parents[2]
CAPTURE_ROOT = WORKSPACE / "captures"
DESIGN_ROOT = WORKSPACE / "design-tokens"
FIXTURE_ROOT = WORKSPACE / "fixtures"


def ensure_dirs() -> None:
    for directory in (DESIGN_ROOT / "ios", DESIGN_ROOT / "android", FIXTURE_ROOT / "shared"):
        directory.mkdir(parents=True, exist_ok=True)


def synthesize_design_tokens(platform: str) -> None:
    ui_dir = CAPTURE_ROOT / platform / "ui"
    tokens_path = DESIGN_ROOT / platform / "tokens.json"
    if tokens_path.exists():
        console.print(f"[green]Existing tokens detected at {tokens_path}; skipping auto-generation")
        return
    if not ui_dir.exists():
        console.print(f"[yellow]{ui_dir} missing; skipping {platform} tokens")
        return

    layout_summary_path = ui_dir / "layout-summary.json"
    layout_payload = {}
    if layout_summary_path.exists():
        layout_payload = json.loads(layout_summary_path.read_text(encoding="utf-8"))

    metrics_map = layout_payload.get("screens", {}) if isinstance(layout_payload, dict) else {}

    run_summary = {}
    latest_run_file = ui_dir / "latest-run.txt"
    if latest_run_file.exists():
        run_id = latest_run_file.read_text(encoding="utf-8").strip()
        summary_path = ui_dir / run_id / "summary.json"
        if summary_path.exists():
            run_summary = json.loads(summary_path.read_text(encoding="utf-8"))

    screens: dict[str, dict] = {}
    for flow in run_summary.get("flows", []):
        slug = flow.get("slug") or flow.get("name")
        if not slug:
            continue
        entry = screens.setdefault(slug, {})
        entry.update(
            {
                "name": flow.get("name"),
                "description": flow.get("description"),
                "status": flow.get("status"),
                "screenshot": flow.get("screenshot"),
                "hierarchy": flow.get("hierarchy"),
                "directory": flow.get("directory"),
                "steps": flow.get("steps"),
            }
        )

    for slug, metrics in metrics_map.items():
        entry = screens.setdefault(slug, {})
        entry["metrics"] = metrics

    tokens_payload = {
        "run_id": run_summary.get("runId") or layout_payload.get("run_id"),
        "screens": screens,
    }

    tokens_path.write_text(json.dumps(tokens_payload, indent=2), encoding="utf-8")
    console.print(f"Wrote design tokens to {tokens_path}")


def synthesize_api_spec() -> None:
    network_dir_ios = CAPTURE_ROOT / "ios" / "network"
    network_dir_android = CAPTURE_ROOT / "android" / "network"
    spec_path = FIXTURE_ROOT / "shared" / "api.yaml"

    flows = []
    for directory in (network_dir_ios, network_dir_android):
        if not directory.exists():
            continue
        flows.extend(sorted(str(p.relative_to(WORKSPACE)) for p in directory.glob("*.mitm")))

    spec = {
        "info": {"title": "Cloned App API", "version": "0.0.1"},
        "x-captured-flows": flows,
    }
    spec_path.write_text(yaml.safe_dump(spec, sort_keys=False), encoding="utf-8")
    console.print(f"Wrote API skeleton to {spec_path}")


def main() -> None:
    ensure_dirs()
    for platform in ("ios", "android"):
        synthesize_design_tokens(platform)
    synthesize_api_spec()


if __name__ == "__main__":
    main()
