#!/usr/bin/env python3
"""Archive source mobile binaries with provenance metadata."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from rich.console import Console

console = Console()


def sha256sum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def archive(
    platform: str,
    binary: Path,
    dest_root: Path,
    version: str | None = None,
    release_notes: str | None = None,
    metadata: dict | None = None,
) -> dict:
    binary = binary.resolve()
    if not binary.exists():
        raise FileNotFoundError(f"Binary not found: {binary}")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    version_segment = version or timestamp
    dest_dir = dest_root / platform / "binaries" / version_segment
    dest_dir.mkdir(parents=True, exist_ok=True)

    dest_file = dest_dir / binary.name
    console.print(f"Archiving {binary} -> {dest_file}")

    data = {
        "platform": platform,
        "source_path": str(binary),
        "stored_path": str(dest_file),
        "filename": binary.name,
        "size_bytes": binary.stat().st_size,
        "sha256": sha256sum(binary),
        "archived_at": timestamp,
        "version": version_segment,
    }
    if release_notes:
        data["release_notes"] = release_notes
    if metadata:
        data.update(metadata)

    dest_file.write_bytes(binary.read_bytes())
    metadata_path = dest_dir / "metadata.json"
    metadata_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    console.print(f"Wrote metadata {metadata_path}")
    return data


def main() -> None:
    parser = argparse.ArgumentParser(description="Archive IPA/APK with provenance metadata")
    parser.add_argument("platform", choices=["ios", "android"], help="Platform of the binary")
    parser.add_argument("binary", type=Path, help="Path to IPA or APK/AAB")
    parser.add_argument("--dest-root", type=Path, default=Path("captures"), help="Root directory for archived binaries")
    parser.add_argument("--version", help="Version label to use for the archive directory")
    parser.add_argument("--release-notes", help="Release notes or summary")
    parser.add_argument("--metadata", help="JSON string of extra metadata")
    args = parser.parse_args()

    extra: dict | None = None
    if args.metadata:
        extra = json.loads(args.metadata)

    archive(
        platform=args.platform,
        binary=args.binary,
        dest_root=args.dest_root,
        version=args.version,
        release_notes=args.release_notes,
        metadata=extra,
    )


if __name__ == "__main__":
    main()
