#!/usr/bin/env python3
"""Remove aged upload artefacts and logs from the intake portal."""
from __future__ import annotations

import argparse
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from rich.console import Console
from rich.table import Table

console = Console()

DEFAULT_RETENTION_DAYS = 1


def collect_targets(root: Path, cutoff: datetime) -> list[Path]:
    targets: list[Path] = []
    if not root.exists():
        return targets
    for child in root.iterdir():
        try:
            mtime = datetime.fromtimestamp(child.stat().st_mtime)
        except FileNotFoundError:
            continue
        if mtime < cutoff:
            targets.append(child)
    return targets


def remove_paths(paths: list[Path]) -> None:
    for path in paths:
        try:
            if path.is_file() or path.is_symlink():
                path.unlink(missing_ok=True)
            else:
                shutil.rmtree(path, ignore_errors=True)
        except Exception as error:  # noqa: BLE001
            console.print(f"[red]Failed to remove {path}: {error}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Prune old uploads/logs produced by the intake portal")
    parser.add_argument(
        "--uploads",
        default="web/storage/uploads",
        help="Directory containing uploaded binaries",
    )
    parser.add_argument(
        "--logs",
        default="web/storage/logs",
        help="Directory containing pipeline log files",
    )
    parser.add_argument(
        "--retention-days",
        type=int,
        default=DEFAULT_RETENTION_DAYS,
        help="Number of days to retain artefacts (default: 1)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List paths that would be removed without deleting them",
    )
    args = parser.parse_args()

    cutoff = datetime.utcnow() - timedelta(days=args.retention_days)
    uploads_root = Path(args.uploads).resolve()
    logs_root = Path(args.logs).resolve()

    upload_targets = collect_targets(uploads_root, cutoff)
    log_targets = collect_targets(logs_root, cutoff)

    table = Table(title="Cleanup summary")
    table.add_column("Category")
    table.add_column("Paths queued")
    table.add_row("Uploads", str(len(upload_targets)))
    table.add_row("Logs", str(len(log_targets)))
    console.print(table)

    if args.dry_run:
        for path in upload_targets + log_targets:
            console.print(f"[yellow]Would remove {path}")
        return

    remove_paths(upload_targets + log_targets)
    console.print("[green]Cleanup complete")


if __name__ == "__main__":
    main()
