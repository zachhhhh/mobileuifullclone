#!/usr/bin/env python3
"""Extract Android resources from APK/AAB using apktool."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import tempfile
from pathlib import Path

from rich.console import Console

console = Console()
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
FONT_EXTS = {".ttf", ".otf", ".ttc"}
ANIMATION_EXTS = {".json", ".lottie"}


def decode_package(app: Path, output: Path) -> Path:
    decoded_dir = output / "decoded"
    subprocess.run(["apktool", "d", "-f", str(app), "-o", str(decoded_dir)], check=True)
    return decoded_dir


def collect_files(decoded_dir: Path, output: Path) -> dict:
    manifest = {
        "images": [],
        "fonts": [],
        "animations": [],
        "xml": [],
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

        dest = output / category / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file, dest)
        manifest[category].append({
            "path": str(rel),
            "size": file.stat().st_size,
        })
    return manifest


def extract(app: Path, output: Path) -> None:
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
        console.print(f"Wrote manifest {manifest_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract Android package assets")
    parser.add_argument("--app", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    extract(Path(args.app), Path(args.output))


if __name__ == "__main__":
    main()
