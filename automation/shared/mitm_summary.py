from __future__ import annotations

import json
from pathlib import Path

from mitmproxy import ctx


class SummaryAddon:
    def __init__(self) -> None:
        self.records = []

    def load(self, loader) -> None:
        loader.add_option(
            "summary_output",
            str,
            "",
            "Path to write JSON summary",
        )
        loader.add_option(
            "summary_include_headers",
            bool,
            True,
            "Whether to include request/response headers",
        )
        loader.add_option(
            "summary_max_body_bytes",
            int,
            512,
            "Trim bodies to this length for samples",
        )

    def response(self, flow) -> None:  # type: ignore[override]
        request = flow.request
        response = flow.response
        record = {
            "method": request.method,
            "url": request.pretty_url,
            "host": request.host,
            "path": request.path,
            "http_version": request.http_version,
            "status_code": response.status_code if response else None,
            "reason": response.reason if response else None,
            "started_at": request.timestamp_start,
            "completed_at": response.timestamp_end if response else None,
            "round_trip_time": (response.timestamp_end - request.timestamp_start)
            if response and response.timestamp_end
            else None,
        }

        if ctx.options.summary_include_headers:
            record["request_headers"] = {
                k: v for k, v in request.headers.items(multi=True)
            }
            if response:
                record["response_headers"] = {
                    k: v for k, v in response.headers.items(multi=True)
                }

        max_bytes = ctx.options.summary_max_body_bytes
        if request.content:
            record["request_body"] = request.content[:max_bytes].decode(
                "utf-8", errors="replace"
            )
        if response and response.content:
            record["response_body"] = response.content[:max_bytes].decode(
                "utf-8", errors="replace"
            )

        self.records.append(record)

    def done(self) -> None:
        output_path = ctx.options.summary_output or "network-summary.json"
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as fh:
            json.dump(self.records, fh, indent=2)
        ctx.log.info(f"Wrote summary to {path}")


addons = [SummaryAddon()]
