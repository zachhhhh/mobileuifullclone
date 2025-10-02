#!/usr/bin/env python3
"""Sync captured API fixtures into backend stub routes."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from rich.console import Console

console = Console()

WORKSPACE = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = WORKSPACE / "fixtures" / "shared"
BACKEND_SRC = WORKSPACE / "backend" / "src"
REPORT_ROOT = WORKSPACE / "reports"

TEMPLATE = """import express from 'express';

const router = express.Router();

{handlers}

export default router;
"""

HANDLER_TEMPLATE = """router.{method}("{path}", (req, res) => {{
  res.status({status}).json({response});
}});
"""


def load_openapi(platform: str) -> dict | None:
    path = FIXTURE_ROOT / f"api-{platform}.json"
    if not path.exists():
        console.print(f"[yellow]OpenAPI skeleton missing for {platform}: {path}")
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def load_endpoint_examples(platform: str) -> dict:
    summary_path = REPORT_ROOT / platform / "network-summary.json"
    if not summary_path.exists():
        return {}
    data = json.loads(summary_path.read_text(encoding="utf-8"))
    return data.get("endpoints", {})


def pick_response(example: dict) -> str:
    body = example.get("response_body") or "{}"
    try:
        parsed = json.loads(body)
        return json.dumps(parsed)
    except json.JSONDecodeError:
        return json.dumps({"body": body})


def synthesize_handlers(platform: str, openapi: dict, endpoint_examples: dict) -> str:
    handlers: list[str] = []
    for path, methods in openapi.get("paths", {}).items():
        for method, details in methods.items():
            responses = details.get("responses", {})
            try:
                status = int(next(iter(responses)))
            except StopIteration:
                status = 200
            except ValueError:
                status = 200
            key = f"{method.upper()} {path}"
            example = endpoint_examples.get(key, {})
            example_body = None
            examples = example.get("examples") if isinstance(example, dict) else None
            if examples:
                example_body = pick_response(examples[0])
            else:
                example_body = json.dumps({"message": "TODO"})

            handlers.append(
                HANDLER_TEMPLATE.format(
                    method=method,
                    path=path,
                    status=status,
                    response=example_body,
                )
            )
    return "\n".join(handlers)


def write_router(platform: str, handlers: str) -> None:
    router_path = BACKEND_SRC / f"{platform}_router.mjs"
    router_path.write_text(TEMPLATE.format(handlers=handlers), encoding="utf-8")
    console.print(f"Wrote router stub {router_path}")


def update_server(platforms: list[str]) -> None:
    server_path = BACKEND_SRC / "server.mjs"
    contents = server_path.read_text(encoding="utf-8")
    marker = "// AUTO-ROUTERS" if "// AUTO-ROUTERS" in contents else None
    if not marker:
        contents = contents.replace(
            "app.use(express.json());",
            "app.use(express.json());\n\n// AUTO-ROUTERS\n",
            1,
        )
        server_path.write_text(contents, encoding="utf-8")
        contents = server_path.read_text(encoding="utf-8")

    lines = contents.splitlines()
    import_index = 0
    for idx, line in enumerate(lines):
        if line.startswith("import"):
            import_index = idx
    imports = []
    mounts = []
    for platform in platforms:
        router_name = f"{platform}Router"
        imports.append(f"import {router_name} from './{platform}_router.mjs';")
        mounts.append(f"app.use('/{platform}', {router_name});")

    new_contents = "\n".join(lines[: import_index + 1] + imports + lines[import_index + 1 :])
    new_contents = new_contents.replace(
        "// AUTO-ROUTERS",
        "// AUTO-ROUTERS\n" + "\n".join(mounts),
    )
    server_path.write_text(new_contents, encoding="utf-8")
    console.print(f"Updated {server_path} with router mounts")


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync backend routes from captured API specs")
    parser.add_argument("--platforms", nargs="*", default=["ios", "android"], help="Platforms to include")
    args = parser.parse_args()

    generated = []
    for platform in args.platforms:
        openapi = load_openapi(platform)
        if not openapi:
            continue
        endpoint_examples = load_endpoint_examples(platform)
        handlers = synthesize_handlers(platform, openapi, endpoint_examples)
        if not handlers:
            console.print(f"[yellow]No handlers generated for {platform}")
            continue
        write_router(platform, handlers)
        generated.append(platform)

    if generated:
        update_server(generated)
    else:
        console.print("[yellow]No routers generated")


if __name__ == "__main__":
    main()
