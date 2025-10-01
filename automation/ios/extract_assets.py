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

        dest = output_dir / category / rel
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
        console.print(f"Unpacking {app} -> {tmp}")
        app_dir = unzip_ipa(app, tmp)
        manifest = collect_files(app_dir, output)
        manifest_path = output / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        console.print(f"Wrote manifest {manifest_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract iOS app assets")
    parser.add_argument("--app", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    extract(Path(args.app), Path(args.output))


if __name__ == "__main__":
    main()
