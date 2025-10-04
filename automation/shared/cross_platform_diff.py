#!/usr/bin/env python3
"""Generate cross-platform parity report comparing iOS and Android artefacts."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from rich.console import Console
from rich.table import Table

console = Console()

WORKSPACE = Path(__file__).resolve().parents[2]
DESIGN_ROOT = WORKSPACE / "design-tokens"
REPORT_ROOT = WORKSPACE / "reports"


def load_json(path: Path) -> dict:
    if not path.exists():
        console.print(f"[yellow]Missing file: {path}")
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        console.print(f"[red]Invalid JSON: {path}")
        return {}


def compare_tokens() -> list[dict[str, str]]:
    ios_tokens = load_json(DESIGN_ROOT / "ios" / "tokens.json")
    android_tokens = load_json(DESIGN_ROOT / "android" / "tokens.json")

    ios_screens = ios_tokens.get("screens", {}) if isinstance(ios_tokens, dict) else {}
    android_screens = android_tokens.get("screens", {}) if isinstance(android_tokens, dict) else {}

    issues: list[dict[str, str]] = []
    ios_only = sorted(set(ios_screens) - set(android_screens))
    android_only = sorted(set(android_screens) - set(ios_screens))

    for screen in ios_only:
        issues.append({
            "type": "missing_on_android",
            "item": screen,
            "detail": "Screen captured on iOS but not Android",
        })
    for screen in android_only:
        issues.append({
            "type": "missing_on_ios",
            "item": screen,
            "detail": "Screen captured on Android but not iOS",
        })

    shared = set(ios_screens) & set(android_screens)
    for screen in sorted(shared):
        ios_entry = ios_screens.get(screen) or {}
        android_entry = android_screens.get(screen) or {}
        ios_metrics = ios_entry.get("metrics") if isinstance(ios_entry, dict) else None
        android_metrics = android_entry.get("metrics") if isinstance(android_entry, dict) else None
        if ios_metrics != android_metrics:
            issues.append({
                "type": "metrics_mismatch",
                "item": screen,
                "detail": "Layout metrics differ between platforms",
            })
    return issues


def write_report(findings: list[dict[str, str]], output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    if not findings:
        content = "# Cross-Platform Parity\n\nAll tracked artefacts are aligned between iOS and Android.\n"
        output.write_text(content, encoding="utf-8")
        console.print(f"[green]No parity issues. Wrote {output}")
        return

    lines = ["# Cross-Platform Parity", ""]
    lines.append("| Type | Item | Detail |")
    lines.append("| ---- | ---- | ------ |")
    for finding in findings:
        lines.append(
            f"| {finding['type']} | {finding['item']} | {finding['detail']} |"
        )
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    console.print(f"[yellow]Parity differences found. Wrote {output}")

    table = Table(title="Cross-Platform Parity Issues")
    table.add_column("Type")
    table.add_column("Item")
    table.add_column("Detail")
    for finding in findings:
        table.add_row(finding["type"], finding["item"], finding["detail"])
    console.print(table)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare iOS and Android artefacts for parity")
    parser.add_argument(
        "--report",
        default=REPORT_ROOT / "cross-platform-parity.md",
        type=Path,
        help="Output path for parity report",
    )
    args = parser.parse_args()

    findings = compare_tokens()
    write_report(findings, args.report)


if __name__ == "__main__":
    main()
