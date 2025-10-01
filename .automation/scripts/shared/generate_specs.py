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
    if not ui_dir.exists():
        console.print(f"[yellow]{ui_dir} missing; skipping {platform} tokens")
        return

    layout_summary_path = ui_dir / "layout-summary.json"
    layout_summary = {}
    if layout_summary_path.exists():
        layout_summary = json.loads(layout_summary_path.read_text(encoding="utf-8"))

    screens = {}
    for screen_dir in sorted(p for p in ui_dir.iterdir() if p.is_dir()):
        screenshot = screen_dir / "screenshot.png"
        xml_path = screen_dir / "source.xml"
        summary = layout_summary.get(screen_dir.name, {})
        screens[screen_dir.name] = {
            "screenshot": str(screenshot.relative_to(WORKSPACE)) if screenshot.exists() else None,
            "hierarchy": str(xml_path.relative_to(WORKSPACE)) if xml_path.exists() else None,
            "metrics": summary,
        }

    tokens_path.write_text(json.dumps({"screens": screens}, indent=2), encoding="utf-8")
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
