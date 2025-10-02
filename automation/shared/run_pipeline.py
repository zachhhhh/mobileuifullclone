#!/usr/bin/env python3
"""Pipeline orchestrator for mobile-app cloning automation.

Starts sub-tasks for binary ingestion, UI capture, network capture,
asset extraction, spec generation, backend sync, clone builds, and reporting.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

import yaml
from rich.console import Console
from rich.table import Table

from automation.shared.archive_binary import archive as archive_binary

console = Console()


def load_config(path: Path) -> dict:
    if not path.exists():
        console.print(f"[bold red]Missing config file: {path}")
        sys.exit(1)
    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    return data


def run(cmd: list[str], cwd: Path | None = None, env: dict | None = None) -> None:
    console.log("$ " + " ".join(cmd))
    completed = subprocess.run(cmd, cwd=cwd, env=env)
    if completed.returncode != 0:
        raise subprocess.CalledProcessError(completed.returncode, cmd)


def ios_capture(config: dict, workspace: Path) -> None:
    remote = config["defaults"]["ios"]["remote_runner"]
    if not remote["host"]:
        console.print("[yellow]IOS_REMOTE_HOST not configured; skipping remote capture trigger")
        return
    script = workspace / ".automation/scripts/ios/run_remote_capture.sh"
    run([str(script), str(workspace)], cwd=workspace)


def android_capture(config: dict, workspace: Path) -> None:
    remote = config["defaults"]["android"]["remote_runner"]
    if not remote["host"]:
        console.print("[yellow]ANDROID_REMOTE_HOST not configured; skipping remote capture trigger")
        return
    script = workspace / ".automation/scripts/android/run_remote_capture.sh"
    run([str(script), str(workspace)], cwd=workspace)


def generate_specs(workspace: Path) -> None:
    run(["python3", ".automation/scripts/shared/generate_specs.py"], cwd=workspace)


def run_backend_sync(workspace: Path) -> None:
    if not (workspace / "backend").exists():
        console.print("[yellow]Backend directory missing; skipping sync tests")
        return
    run(["npm", "test"], cwd=workspace / "backend")


def build_clients(workspace: Path) -> None:
    ios_dir = workspace / "client-ios"
    android_dir = workspace / "client-android"
    if ios_dir.exists():
        run(["fastlane", "clone_build"], cwd=ios_dir)
    else:
        console.print("[yellow]client-ios missing; skip")
    if android_dir.exists():
        run(["./gradlew", "cloneBuild"], cwd=android_dir)
    else:
        console.print("[yellow]client-android missing; skip")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run mobile clone automation pipeline")
    parser.add_argument("platform", choices=["ios", "android"], help="Platform to process")
    parser.add_argument("binary", type=Path, help="Path to IPA or APK/AAB file")
    parser.add_argument("--config", default=os.getenv("AUTOMATION_CONFIG", ".automation/config.yaml"))
    args = parser.parse_args()

    workspace = Path(os.getcwd())
    config_path = workspace / args.config
    config = load_config(config_path)

    captures_root = workspace / config["defaults"]["artifact_root"]
    archive_info = archive_binary(
        platform=args.platform,
        binary=args.binary,
        dest_root=captures_root,
        version=os.getenv("BINARY_VERSION"),
        release_notes=os.getenv("BINARY_RELEASE_NOTES"),
    )
    binary_out = Path(archive_info["stored_path"])

    with console.status("Running capture"):
        if args.platform == "ios":
            ios_capture(config, workspace)
        else:
            android_capture(config, workspace)

    summarize_network_cmd = [
        "python3",
        "automation/shared/summarize_network.py",
        args.platform,
    ]
    run(summarize_network_cmd, cwd=workspace)

    security_cmd = [
        "python3",
        "automation/shared/security_audit.py",
        args.platform,
    ]
    run(security_cmd, cwd=workspace)

    run([
        "python3",
        "backend/src/sync_endpoints.py",
        "--platforms",
        args.platform,
    ], cwd=workspace)

    run([
        "python3",
        "automation/shared/sync_tokens.py",
        args.platform,
    ], cwd=workspace)

    run([
        "python3",
        "automation/shared/qa_check.py",
        args.platform,
    ], cwd=workspace)

    run([
        "python3",
        "automation/shared/release_report.py",
        args.platform,
    ], cwd=workspace)

    generate_specs(workspace)
    run_backend_sync(workspace)
    build_clients(workspace)

    table = Table(title="Pipeline Complete")
    table.add_column("Platform")
    table.add_column("Binary")
    table.add_row(args.platform, binary_out.as_posix())
    console.print(table)


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as err:
        console.print(f"[bold red]Command failed: {' '.join(err.cmd)}")
        sys.exit(err.returncode)
    except Exception as exc:  # noqa: BLE001
        console.print(f"[bold red]{exc}")
        sys.exit(1)
