#!/usr/bin/env python3
"""Perform baseline privacy/security audit on extracted assets and configs."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from rich.console import Console
from rich.table import Table

console = Console()

SECRET_PATTERNS = {
    "AWS Access Key": re.compile(r"AKIA[0-9A-Z]{16}"),
    "Google API Key": re.compile(r"AIza[0-9A-Za-z-_]{35}"),
    "Private Key": re.compile(r"-----BEGIN (RSA|DSA|EC) PRIVATE KEY-----"),
    "JWT": re.compile(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"),
}

PII_KEYWORDS = [
    "ssn",
    "social security",
    "credit card",
    "password",
    "secret",
    "private",
]

CONFIG_FILENAMES = {
    "plist": re.compile(r"\.plist$", re.IGNORECASE),
    "json": re.compile(r"\.json$", re.IGNORECASE),
    "xml": re.compile(r"\.xml$", re.IGNORECASE),
    "strings": re.compile(r"\.strings$", re.IGNORECASE),
}


def scan_file(path: Path) -> dict:
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:  # noqa: BLE001
        return {}

    findings: dict[str, list[str]] = {}

    for name, pattern in SECRET_PATTERNS.items():
        matches = pattern.findall(text)
        if matches:
            findings.setdefault(name, []).extend(matches[:5])

    lowered = text.lower()
    for keyword in PII_KEYWORDS:
        if keyword in lowered:
            findings.setdefault("PII keyword", []).append(keyword)

    return findings


def summarize_asset_dir(asset_dir: Path) -> list[dict]:
    rows: list[dict] = []
    for file in asset_dir.rglob("*"):
        if not file.is_file():
            continue
        findings = scan_file(file)
        if findings:
            rows.append({
                "path": str(file.relative_to(asset_dir)),
                "findings": findings,
            })
    return rows


def find_config_files(base_dir: Path) -> list[Path]:
    results: list[Path] = []
    for file in base_dir.rglob("*"):
        if not file.is_file():
            continue
        if any(pattern.search(file.name) for pattern in CONFIG_FILENAMES.values()):
            results.append(file)
    return results


def audit_platform(platform: str, base: Path, report_dir: Path) -> dict:
    asset_dir = base / platform / "assets"
    results = {
        "platform": platform,
        "suspect_files": [],
        "config_files": [],
    }
    if asset_dir.exists():
        results["suspect_files"] = summarize_asset_dir(asset_dir)

    config_files = find_config_files(base / platform)
    results["config_files"] = [str(path.relative_to(base)) for path in config_files]

    report_dir.mkdir(parents=True, exist_ok=True)
    output = report_dir / "security-audit.json"
    output.write_text(json.dumps(results, indent=2), encoding="utf-8")

    table = Table(title=f"Security Audit ({platform})")
    table.add_column("Type")
    table.add_column("Count")
    table.add_row("Suspect Files", str(len(results["suspect_files"])))
    table.add_row("Config Files", str(len(results["config_files"])))
    console.print(table)

    if results["suspect_files"]:
        console.print(f"[bold yellow]Review flagged assets in {output}")
    else:
        console.print("[bold green]No secrets/PII detected in assets.")

    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Baseline security audit")
    parser.add_argument("platform", choices=["ios", "android", "both"], help="Platform to audit")
    parser.add_argument("--captures", default="captures", help="Root directory containing captured data")
    parser.add_argument("--reports", default="reports", help="Directory to place reports")
    args = parser.parse_args()

    base = Path(args.captures)
    reports = Path(args.reports)

    if args.platform in ("ios", "both"):
        audit_platform("ios", base, reports / "ios")
    if args.platform in ("android", "both"):
        audit_platform("android", base, reports / "android")


if __name__ == "__main__":
    main()
