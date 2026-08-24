#!/usr/bin/env python3
"""Measure MCP service startup, first-query and resident hot-query latency."""

from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
import time
from pathlib import Path


def _roundtrip(process: subprocess.Popen, payload: dict) -> tuple[dict, float]:
    started = time.perf_counter()
    assert process.stdin is not None
    assert process.stdout is not None
    process.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
    process.stdin.flush()
    line = process.stdout.readline()
    elapsed = time.perf_counter() - started
    if not line:
        stderr = process.stderr.read()[-500:] if process.stderr else ""
        raise RuntimeError(f"MCP server closed stdout: {stderr}")
    return json.loads(line), elapsed


def measure(db: Path, model: str, query_text: str) -> dict:
    # Preserve the caller's selected installation. In fresh-wheel CI, forcing
    # the repository's src/ directory here would silently benchmark source.
    env = dict(os.environ)
    command = [
        sys.executable, "-m", "ue_knowledge.cli", "serve",
        "--db", str(db), "--model", model,
    ]
    process_started = time.perf_counter()
    process = subprocess.Popen(
        command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True, encoding="utf-8", env=env,
    )
    process_spawn_seconds = time.perf_counter() - process_started
    try:
        initialize, initialize_seconds = _roundtrip(
            process,
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
                "protocolVersion": "2024-11-05", "capabilities": {},
                "clientInfo": {"name": "ue-kb-mcp-benchmark", "version": "1"},
            }},
        )
        request = lambda request_id: {
            "jsonrpc": "2.0", "id": request_id, "method": "tools/call",
            "params": {"name": "ue_kb_query", "arguments": {"query": query_text}},
        }
        first, first_query_seconds = _roundtrip(process, request(2))
        hot, hot_query_seconds = _roundtrip(process, request(3))
        if any("result" not in response for response in (initialize, first, hot)):
            raise RuntimeError("MCP benchmark received an error response")
        return {
            "schema_version": 1,
            "query": query_text,
            # The initialize response is the readiness boundary for the
            # resident stdio service.  Do not include first and hot query
            # work in the startup metric; those are reported separately.
            "server_startup_seconds": initialize_seconds,
            "process_spawn_seconds": process_spawn_seconds,
            "initialize_roundtrip_seconds": initialize_seconds,
            "first_query_seconds": first_query_seconds,
            "hot_query_seconds": hot_query_seconds,
            "passed": True,
        }
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def compare_baseline(
    payload: dict,
    baseline: dict,
    *,
    max_regression: float = 0.20,
    absolute_tolerance_seconds: float = 0.0002,
) -> dict:
    """Attach same-machine MCP latency regression checks to a report.

    The baseline is deliberately explicit and optional: CI runners are not a
    same-machine performance comparison. A release operator can pass a
    0.6.x report captured on the same machine and fail closed when any metric
    exceeds the allowed relative regression. Sub-millisecond hot-query
    measurements use a small absolute jitter tolerance.
    """
    metrics = (
        "server_startup_seconds",
        "first_query_seconds",
        "hot_query_seconds",
    )
    failures = []
    regressions = {}
    for metric in metrics:
        current = float(payload.get(metric, 0.0))
        previous = float(baseline.get(metric, 0.0))
        if previous <= 0:
            failures.append({"metric": metric, "reason": "baseline must be positive"})
            continue
        relative = (current - previous) / previous
        regressions[metric] = relative
        # A single sub-millisecond round trip is dominated by scheduler and
        # pipe jitter. Keep a hard absolute tolerance for that one metric;
        # larger timings still use the requested relative gate.
        if previous < 0.001:
            absolute_delta = current - previous
            exceeded = absolute_delta > absolute_tolerance_seconds and not math.isclose(
                absolute_delta,
                absolute_tolerance_seconds,
                rel_tol=0.0,
                abs_tol=0.000001,
            )
        else:
            exceeded = relative > max_regression
        if exceeded:
            failures.append({
                "metric": metric,
                "baseline": previous,
                "current": current,
                "relative_regression": relative,
                "allowed": max_regression,
                "absolute_tolerance_seconds": absolute_tolerance_seconds,
            })
    payload["baseline"] = {
        "metrics": {metric: float(baseline.get(metric, 0.0)) for metric in metrics},
        "max_regression": max_regression,
        "absolute_tolerance_seconds": absolute_tolerance_seconds,
        "relative_regression": regressions,
        "failures": failures,
        "passed": not failures,
    }
    payload["passed"] = bool(payload.get("passed") and not failures)
    return payload


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--query", default="collision response component")
    parser.add_argument(
        "--baseline",
        type=Path,
        help="optional same-machine JSON report from the previous release",
    )
    parser.add_argument(
        "--max-regression",
        type=float,
        default=0.20,
        help="maximum relative latency regression when --baseline is supplied",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    payload = measure(args.db, args.model, args.query)
    if args.baseline:
        baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
        payload = compare_baseline(
            payload,
            baseline,
            max_regression=args.max_regression,
        )
    rendered = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if payload.get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
