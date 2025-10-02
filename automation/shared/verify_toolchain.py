#!/usr/bin/env python3
"""Verify local toolchain prerequisites for iOS/Android capture runners."""
from __future__ import annotations

import argparse
import platform
import shutil
import subprocess
import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table

console = Console()

COMMON_COMMANDS = [
    "node",
    "npm",
    "python3",
    "pip3",
    "git",
    "mitmdump",
]

IOS_COMMANDS = [
    "appium",
    "xcrun",
    "xcodebuild",
]

ANDROID_COMMANDS = [
    "appium",
    "adb",
    "emulator",
    "apktool",
    "java",
]


def command_version(cmd: str) -> str | None:
    try:
        result = subprocess.run([cmd, "--version"], check=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    except Exception:  # noqa: BLE001
        return None
    output = result.stdout.strip().splitlines()
    return output[0] if output else None


def check_command(cmd: str) -> tuple[bool, str | None]:
    location = shutil.which(cmd)
    if not location:
        return False, None
    return True, command_version(cmd)


def verify(commands: list[str]) -> list[tuple[str, bool, str | None]]:
    rows = []
    for cmd in commands:
        ok, version = check_command(cmd)
        rows.append((cmd, ok, version))
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify capture toolchain")
    parser.add_argument("platform", choices=["ios", "android", "both"], help="Which platform requirements to check")
    parser.add_argument("--additional", nargs="*", help="Additional commands to verify")
    args = parser.parse_args()

    commands = COMMON_COMMANDS.copy()
    if args.platform in ("ios", "both"):
        commands.extend(IOS_COMMANDS)
    if args.platform in ("android", "both"):
        commands.extend(ANDROID_COMMANDS)
    if args.additional:
        commands.extend(args.additional)

    rows = verify(commands)

    table = Table(title=f"Toolchain Verification ({platform.system()})")
    table.add_column("Command")
    table.add_column("Status")
    table.add_column("Version")

    failures = []
    for cmd, ok, version in rows:
        status = "✅" if ok else "❌"
        table.add_row(cmd, status, version or "<missing>")
        if not ok:
            failures.append(cmd)

    console.print(table)

    if failures:
        console.print(f"[bold red]Missing commands: {', '.join(failures)}")
        sys.exit(1)

    console.print("[bold green]All required commands are available.")


if __name__ == "__main__":
    main()
