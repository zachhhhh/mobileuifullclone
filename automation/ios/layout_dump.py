#!/usr/bin/env python3
"""Summarise iOS UI hierarchy dumps into layout metrics."""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from lxml import etree
from rich.console import Console

console = Console()


def parse_xml(xml_path: Path) -> dict:
    tree = etree.parse(str(xml_path))
    elements = tree.xpath("//*[starts-with(name(), 'XCUIElementType')]")
    classes = Counter(elem.tag for elem in elements)
    accessibility = [
        {
            "label": elem.get("label"),
            "identifier": elem.get("identifier"),
            "value": elem.get("value"),
        }
        for elem in elements
        if elem.get("label") or elem.get("value")
    ]
    frames = []
    for elem in elements:
        frames.append(
            {
                "type": elem.tag,
                "rect": {
                    "x": float(elem.get("x", 0)),
                    "y": float(elem.get("y", 0)),
                    "width": float(elem.get("width", 0)),
                    "height": float(elem.get("height", 0)),
                },
            }
        )
    return {
        "element_count": len(elements),
        "class_frequency": classes,
        "accessibility": accessibility,
        "frames": frames,
    }


def normalise_summary(summary: dict[str, dict]) -> dict[str, dict]:
    normalised: dict[str, dict] = {}
    for screen, data in summary.items():
        normalised[screen] = {
            "element_count": data["element_count"],
            "class_frequency": dict(data["class_frequency"]),
            "accessibility": data["accessibility"],
        }
    return normalised


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

    # fallback: choose most recent directory with sources
    candidates = [d for d in base.iterdir() if d.is_dir() and d.name != "latest-run.txt"]
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    for candidate in candidates:
        sources = sorted(candidate.rglob("source.xml"))
        if sources:
            return sources, candidate.name

    # fallback: any source files directly under base
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
    parser = argparse.ArgumentParser(description="Summarise iOS layout dumps")
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
