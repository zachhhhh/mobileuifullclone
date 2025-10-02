#!/usr/bin/env python3
"""Sync generated design tokens and assets into client projects."""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from rich.console import Console

console = Console()

WORKSPACE = Path(__file__).resolve().parents[2]
TOKENS_ROOT = WORKSPACE / "design-tokens"

def sync_ios() -> None:
    source = TOKENS_ROOT / "ios" / "tokens.json"
    if not source.exists():
        console.print(f"[yellow]Missing iOS tokens at {source}")
        return
    resources_dir = WORKSPACE / "client-ios" / "Sources" / "CloneUI" / "Resources"
    resources_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, resources_dir / "tokens.json")
    console.print(f"Copied iOS tokens to {resources_dir}")


def sync_android() -> None:
    source = TOKENS_ROOT / "android" / "tokens.json"
    if not source.exists():
        console.print(f"[yellow]Missing Android tokens at {source}")
        return
    assets_dir = WORKSPACE / "client-android" / "app" / "src" / "main" / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, assets_dir / "tokens.json")
    console.print(f"Copied Android tokens to {assets_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync design tokens into client projects")
    parser.add_argument("platform", choices=["ios", "android", "both"], help="Platform to sync")
    args = parser.parse_args()

    if args.platform in ("ios", "both"):
        sync_ios()
    if args.platform in ("android", "both"):
        sync_android()


if __name__ == "__main__":
    main()
