#!/usr/bin/env python3
"""Summarise Android UI hierarchy dumps into layout metrics."""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

from lxml import etree
from rich.console import Console

console = Console()

BOUNDS_RE = re.compile(r"\[(?P<x1>\d+),(?P<y1>\d+)\]\[(?P<x2>\d+),(?P<y2>\d+)\]")


def parse_bounds(bounds: str) -> dict[str, float]:
    match = BOUNDS_RE.match(bounds)
    if not match:
        return {"x": 0.0, "y": 0.0, "width": 0.0, "height": 0.0}
    x1 = float(match.group("x1"))
    y1 = float(match.group("y1"))
    x2 = float(match.group("x2"))
    y2 = float(match.group("y2"))
    return {
        "x": x1,
        "y": y1,
        "width": x2 - x1,
        "height": y2 - y1,
    }


def parse_xml(xml_path: Path) -> dict:
    tree = etree.parse(str(xml_path))
    elements = tree.findall(".//node")
    classes = Counter(elem.get("class") for elem in elements if elem.get("class"))
    accessibility = [
        {
            "content_desc": elem.get("content-desc"),
            "text": elem.get("text"),
        }
        for elem in elements
        if elem.get("content-desc") or elem.get("text")
    ]
    frames = []
    for elem in elements:
        frames.append(
            {
                "type": elem.get("class"),
                "rect": parse_bounds(elem.get("bounds", "")),
            }
        )
    return {
        "element_count": len(elements),
        "class_frequency": classes,
        "accessibility": accessibility,
        "frames": frames,
    }


def normalise_summary(summary: dict[str, dict]) -> dict[str, dict]:
    return {
        screen: {
            "element_count": data["element_count"],
            "class_frequency": dict(data["class_frequency"]),
            "accessibility": data["accessibility"],
        }
        for screen, data in summary.items()
    }


def gather_sources(base: Path, run: str | None) -> tuple[list[Path], str | None]:
    if not base.exists():
        return [], None

    if run and run not in {"latest", "all"}:
        target = base / run
        if target.exists():
            return sorted(target.rglob("source.xml")), target.name
        console.print(f"[yellow]Run {run} not found; falling back to latest")

    if run == "all":
        return sorted(base.rglob("source.xml")), None

    latest_file = base / "latest-run.txt"
    if latest_file.exists():
        run_id = latest_file.read_text(encoding="utf-8").strip()
        target = base / run_id
        if target.exists():
            sources = sorted(target.rglob("source.xml"))
            if sources:
                return sources, run_id

    candidates = [d for d in base.iterdir() if d.is_dir() and d.name != "latest-run.txt"]
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    for candidate in candidates:
        sources = sorted(candidate.rglob("source.xml"))
        if sources:
            return sources, candidate.name

    direct_sources = sorted(base.glob("source.xml"))
    if direct_sources:
        return direct_sources, None

    return [], None


def summarise(sources: list[Path]) -> dict[str, dict]:
    summary: dict[str, dict] = {}
    for xml in sources:
        screen = xml.parent.name
        console.print(f"Processing {xml}")
        summary[screen] = parse_xml(xml)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarise Android layout dumps")
    parser.add_argument("--input", required=True, help="Directory containing captured UI artefacts")
    parser.add_argument("--output", required=True, help="Destination JSON file")
    parser.add_argument("--run", default="latest", help="Run identifier ('latest', 'all', or specific run id)")
    args = parser.parse_args()

    input_dir = Path(args.input)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    sources, run_id = gather_sources(input_dir, args.run)
    if not sources:
        console.print(f"[yellow]No UI hierarchies found in {input_dir}")
        output_path.write_text(json.dumps({"run_id": run_id, "screens": {}}, indent=2), encoding="utf-8")
        return

    summary = summarise(sources)
    payload = {
        "run_id": run_id,
        "screens": normalise_summary(summary),
    }
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    console.print(f"Wrote layout summary for run '{run_id}' to {output_path}")


if __name__ == "__main__":
    main()
