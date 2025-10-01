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
        bounds = parse_bounds(elem.get("bounds", ""))
        frames.append({
            "type": elem.get("class"),
            "rect": bounds,
        })
    return {
        "element_count": len(elements),
        "class_frequency": classes,
        "accessibility": accessibility,
        "frames": frames,
    }


def normalise_summary(summary: dict) -> dict:
    return {
        screen: {
            "element_count": data["element_count"],
            "class_frequency": dict(data["class_frequency"]),
            "accessibility": data["accessibility"],
        }
        for screen, data in summary.items()
    }


def summarise(input_dir: Path) -> dict:
    summary: dict[str, dict] = {}
    for xml in input_dir.rglob("source.xml"):
        screen = xml.parent.name
        console.print(f"Processing {xml}")
        summary[screen] = parse_xml(xml)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarise Android layout dumps")
    parser.add_argument("--input", required=True, help="Directory containing Appium XML dumps")
    parser.add_argument("--output", required=True, help="Destination JSON file")
    args = parser.parse_args()

    input_dir = Path(args.input)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    summary = summarise(input_dir)
    output_path.write_text(json.dumps(normalise_summary(summary), indent=2), encoding="utf-8")
    console.print(f"Wrote layout summary to {output_path}")


if __name__ == "__main__":
    main()
