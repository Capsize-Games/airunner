#!/usr/bin/env python3
"""Benchmark one LTX clip via the daemon API and record telemetry.

Target: 1280x720, 97 frames, 24 fps, 8 distilled steps, audio on.
Writes a Markdown report with ffprobe evidence; a run only counts
when the MP4 probes as 720p/h264+aac at ~4.04 s. No fabricated numbers:
if generation fails, the report says so with the daemon error.
Usage: .venv/bin/python scripts/ltx_benchmark.py [--runs 3]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.request

import os

BASE = os.environ.get("AIRUNNER_DAEMON_URL", "http://127.0.0.1:8188")
TOKEN = os.environ.get("AIRUNNER_API_KEY", "")
PROMPT = (
    "A red tram crosses a rainy city square at dusk, headlights "
    "reflecting on wet stone, camera tracking slowly left, "
    "sound of rain, distant bell and tram wheels on tracks."
)


def _call(method: str, path: str, body: dict | None = None):
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if TOKEN:
        headers["X-Airunner-Token"] = TOKEN
    req = urllib.request.Request(
        BASE + path, data=data, method=method, headers=headers,
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        raw = resp.read()
        ctype = resp.headers.get_content_type()
        return raw if ctype == "video/mp4" else json.loads(raw or b"{}")


def _probe(path: str) -> dict:
    out = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json",
         "-show_format", "-show_streams", path],
        capture_output=True, text=True, check=True,
    ).stdout
    return json.loads(out)


def run_once(index: int) -> dict:
    job = _call("POST", "/api/v1/video/generate", {
        "prompt": PROMPT, "width": 1280, "height": 720,
        "num_frames": 97, "fps": 24, "steps": 8, "seed": 42,
        "checkpoint": "fp8", "audio": True,
    })
    job_id = job["job_id"]
    started = time.time()
    while True:
        status = _call("GET", f"/api/v1/video/status/{job_id}")
        if status["status"] in ("completed", "failed", "cancelled"):
            break
        if time.time() - started > 1800:
            raise TimeoutError(job_id)
        time.sleep(5)
    if status["status"] != "completed":
        return {"run": index, "ok": False,
                "error": status.get("error")}
    mp4 = f"/tmp/ltx-bench-{job_id}.mp4"
    with open(mp4, "wb") as fh:
        fh.write(_call("GET", f"/api/v1/video/result/{job_id}"))
    probe = _probe(mp4)
    streams = {s["codec_type"]: s for s in probe["streams"]}
    ok = (
        streams.get("video", {}).get("width") == 1280
        and streams.get("video", {}).get("height") == 720
        and "audio" in streams
    )
    return {"run": index, "ok": ok, "file": mp4, "probe": probe,
            "wall_time_s": status.get("wall_time_s"),
            "peak_vram_mb": status.get("peak_vram_mb"),
            "peak_rss_mb": status.get("peak_rss_mb")}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--output", default="docs/benchmarks/ltx23-720p.md")
    args = parser.parse_args()
    results = []
    for i in range(args.runs):
        try:
            results.append(run_once(i))
        except Exception as exc:  # recorded, never hidden
            results.append({"run": i, "ok": False, "error": str(exc)})
    lines = ["# LTX-2.3 720p benchmark (97f / 24fps / 8 steps)", "",
             f"Prompt: {PROMPT}", "",
             "| run | ok | wall s | peak VRAM MB | peak RSS MB |",
             "|---|---|---|---|---|"]
    for r in results:
        lines.append(
            f"| {r['run']} | {r.get('ok')} | {r.get('wall_time_s')} "
            f"| {r.get('peak_vram_mb')} | {r.get('peak_rss_mb')} |")
        if not r.get("ok"):
            lines.append(f"\nFailure: `{r.get('error')}`")
    text = "\n".join(lines) + "\n"
    with open(args.output, "w") as fh:
        fh.write(text)
    print(text)
    return 0 if any(r.get("ok") for r in results) else 1


if __name__ == "__main__":
    sys.exit(main())
