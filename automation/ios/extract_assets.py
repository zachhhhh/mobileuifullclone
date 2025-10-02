#!/usr/bin/env python3
"""Extract assets from IPA bundles into structured directories."""
from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from pathlib import Path

from rich.console import Console

console = Console()
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
FONT_EXTS = {".ttf", ".otf", ".ttc"}
ANIMATION_EXTS = {".json", ".lottie"}


def unzip_ipa(ipa_path: Path, target: Path) -> Path:
    shutil.unpack_archive(str(ipa_path), target)
    payload_dir = next(target.glob("Payload/*.app"))
    return payload_dir


def collect_files(app_dir: Path, output_dir: Path) -> dict:
    manifest = {
        "images": [],
        "fonts": [],
        "animations": [],
        "strings": [],
        "databases": [],
        "other": [],
    }
    for file in app_dir.rglob("*"):
        if not file.is_file():
            continue
        rel = file.relative_to(app_dir)
        suffix = file.suffix.lower()
        category = "other"
        if suffix in IMAGE_EXTS:
            category = "images"
        elif suffix in FONT_EXTS:
            category = "fonts"
        elif suffix in ANIMATION_EXTS and "lottie" in rel.parts:
            category = "animations"
        elif suffix in {".strings", ".json"} and "lproj" in rel.parts:
            category = "strings"
        elif suffix in {".sqlite", ".db"}:
            category = "databases"

        dest = output_dir / category / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file, dest)
        manifest[category].append({
            "path": str(rel),
            "size": file.stat().st_size,
        })
    return manifest


def build_summary(manifest: dict[str, list[dict]]) -> dict:
    summary = {
        "categories": {},
        "totals": {
            "files": 0,
            "bytes": 0,
        },
    }

    for category, items in manifest.items():
        count = len(items)
        size = sum(item["size"] for item in items)
        summary["categories"][category] = {
            "count": count,
            "bytes": size,
            "examples": [item["path"] for item in items[:5]],
        }
        summary["totals"]["files"] += count
        summary["totals"]["bytes"] += size

    return summary


def extract(app: Path, output: Path, report: Path | None = None) -> None:
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        console.print(f"Unpacking {app} -> {tmp}")
        app_dir = unzip_ipa(app, tmp)
        manifest = collect_files(app_dir, output)
        manifest_path = output / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        summary = build_summary(manifest)
        summary_path = output / "summary.json"
        summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
        console.print(f"Wrote manifest {manifest_path}")
        if report:
            report.parent.mkdir(parents=True, exist_ok=True)
            report.write_text(json.dumps(summary, indent=2), encoding="utf-8")
            console.print(f"Wrote asset summary {report}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract iOS app assets")
    parser.add_argument("--app", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", help="Optional path to write summary report")
    args = parser.parse_args()

    extract(Path(args.app), Path(args.output), Path(args.report) if args.report else None)


if __name__ == "__main__":
    main()
