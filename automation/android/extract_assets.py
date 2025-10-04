#!/usr/bin/env python3
"""Extract Android resources from APK/AAB using apktool."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

from rich.console import Console

console = Console()
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
FONT_EXTS = {".ttf", ".otf", ".ttc"}
ANIMATION_EXTS = {".json", ".lottie"}


def decode_package(app: Path, output: Path) -> Path:
    decoded_dir = output / "decoded"
    try:
        subprocess.run(
            ["apktool", "d", "-f", str(app), "-o", str(decoded_dir)],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        return decoded_dir
    except FileNotFoundError:
        console.print("[yellow]apktool not available; falling back to zip extraction")
    except subprocess.CalledProcessError as err:
        console.print(f"[yellow]apktool failed ({err}); using zip fallback")

    fallback_dir = output / "zip_fallback"
    if fallback_dir.exists():
        shutil.rmtree(fallback_dir)
    fallback_dir.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(app) as archive:
            archive.extractall(fallback_dir)
    except zipfile.BadZipFile:
        console.print(f"[red]Unable to decode {app}: not a valid APK/AAB")
        return fallback_dir
    return fallback_dir


def collect_files(decoded_dir: Path, output: Path) -> dict:
    manifest = {
        "images": [],
        "fonts": [],
        "animations": [],
        "xml": [],
        "strings": [],
        "databases": [],
        "other": [],
    }
    for file in decoded_dir.rglob("*"):
        if not file.is_file():
            continue
        rel = file.relative_to(decoded_dir)
        suffix = file.suffix.lower()
        category = "other"
        if suffix in IMAGE_EXTS:
            category = "images"
        elif suffix in FONT_EXTS:
            category = "fonts"
        elif suffix in ANIMATION_EXTS and "lottie" in rel.parts:
            category = "animations"
        elif suffix == ".xml":
            category = "xml"
        elif suffix in {".json", ".txt"} and "res" in rel.parts:
            category = "strings"
        elif suffix in {".db", ".sqlite"}:
            category = "databases"

        dest = output / category / rel
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
        console.print(f"Decoding {app}")
        decoded_dir = decode_package(app, tmp)
        manifest = collect_files(decoded_dir, output)
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
    parser = argparse.ArgumentParser(description="Extract Android package assets")
    parser.add_argument("--app", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--report", help="Optional path to write summary report")
    args = parser.parse_args()

    extract(Path(args.app), Path(args.output), Path(args.report) if args.report else None)


if __name__ == "__main__":
    main()
