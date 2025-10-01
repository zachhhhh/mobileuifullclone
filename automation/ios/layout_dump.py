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
        rect_data = {
            "x": float(elem.get("x", 0)),
            "y": float(elem.get("y", 0)),
            "width": float(elem.get("width", 0)),
            "height": float(elem.get("height", 0)),
        }
        frames.append({
            "type": elem.tag,
            "rect": rect_data,
        })
    return {
        "element_count": len(elements),
        "class_frequency": classes,
        "accessibility": accessibility,
        "frames": frames,
    }


def normalise_summary(summary: dict) -> dict:
    normalised = {}
    for screen, data in summary.items():
        normalised[screen] = {
            "element_count": data["element_count"],
            "class_frequency": dict(data["class_frequency"]),
            "accessibility": data["accessibility"],
        }
    return normalised


def summarise(input_dir: Path) -> dict:
    summary: dict[str, dict] = {}
    for xml in input_dir.rglob("source.xml"):
        screen = xml.parent.name
        console.print(f"Processing {xml}")
        summary[screen] = parse_xml(xml)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarise iOS layout dumps")
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
