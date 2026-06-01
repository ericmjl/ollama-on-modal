# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx"]
# ///

"""Benchmark cold and warm start latency for the Modal Ollama deployment."""

from __future__ import annotations

import json
import os
import sys
import time
from dataclasses import dataclass

import httpx

ENDPOINT = os.environ.get(
    "MODAL_ENDPOINT_URL",
    "https://ericmjl--ollama-service-ollamaservice-server.modal.run",
).rstrip("/")
MODEL = os.environ.get("BENCHMARK_MODEL", "qwen3.6:35b")
PROMPT = os.environ.get(
    "BENCHMARK_PROMPT", "Reply with exactly one word: hello."
)
GENERATE_TIMEOUT = float(os.environ.get("BENCHMARK_TIMEOUT", "600"))
IDLE_SECONDS = int(os.environ.get("BENCHMARK_IDLE_SECONDS", "130"))


@dataclass
class GenerateResult:
    label: str
    wall_seconds: float
    http_status: int
    load_seconds: float | None
    prompt_eval_seconds: float | None
    eval_seconds: float | None
    total_seconds: float | None
    response_preview: str
    error: str | None = None


def _ns_to_s(value: int | float | None) -> float | None:
    if value is None:
        return None
    return value / 1_000_000_000


def generate(label: str) -> GenerateResult:
    url = f"{ENDPOINT}/api/generate"
    payload = {"model": MODEL, "prompt": PROMPT, "stream": False}

    start = time.perf_counter()
    try:
        with httpx.Client(timeout=GENERATE_TIMEOUT, follow_redirects=True) as client:
            response = client.post(url, json=payload)
        wall = time.perf_counter() - start
    except httpx.HTTPError as exc:
        return GenerateResult(
            label=label,
            wall_seconds=time.perf_counter() - start,
            http_status=0,
            load_seconds=None,
            prompt_eval_seconds=None,
            eval_seconds=None,
            total_seconds=None,
            response_preview="",
            error=str(exc),
        )

    preview = ""
    load_s = prompt_s = eval_s = total_s = None
    if response.status_code == 200:
        data = response.json()
        preview = (data.get("response") or "")[:80]
        load_s = _ns_to_s(data.get("load_duration"))
        prompt_s = _ns_to_s(data.get("prompt_eval_duration"))
        eval_s = _ns_to_s(data.get("eval_duration"))
        total_s = _ns_to_s(data.get("total_duration"))
    else:
        preview = response.text[:120]

    return GenerateResult(
        label=label,
        wall_seconds=wall,
        http_status=response.status_code,
        load_seconds=load_s,
        prompt_eval_seconds=prompt_s,
        eval_seconds=eval_s,
        total_seconds=total_s,
        response_preview=preview,
        error=None if response.status_code == 200 else response.text[:200],
    )


def ping_version() -> tuple[int, float]:
    start = time.perf_counter()
    with httpx.Client(timeout=120.0) as client:
        response = client.get(f"{ENDPOINT}/api/version")
    return response.status_code, time.perf_counter() - start


def print_result(result: GenerateResult) -> None:
    print(f"\n=== {result.label} ===")
    print(f"HTTP status:     {result.http_status}")
    print(f"Wall clock:      {result.wall_seconds:.2f}s")
    if result.load_seconds is not None:
        print(f"Model load:      {result.load_seconds:.2f}s  (Ollama load_duration)")
    if result.prompt_eval_seconds is not None:
        print(f"Prompt eval:     {result.prompt_eval_seconds:.2f}s")
    if result.eval_seconds is not None:
        print(f"Generation:      {result.eval_seconds:.2f}s  (Ollama eval_duration)")
    if result.total_seconds is not None:
        print(f"Ollama total:    {result.total_seconds:.2f}s  (server-side)")
    if result.response_preview:
        print(f"Response:        {result.response_preview!r}")
    if result.error:
        print(f"Error:           {result.error}")


def main() -> None:
    print("Modal Ollama benchmark")
    print(f"Endpoint: {ENDPOINT}")
    print(f"Model:    {MODEL}")
    print(f"Prompt:   {PROMPT!r}")

    print("\nWaiting for idle period so the next request is a cold start...")
    print(f"(sleeping {IDLE_SECONDS}s for scaledown_window=120s + buffer)")
    time.sleep(IDLE_SECONDS)

    status, version_wall = ping_version()
    print(f"\nWake ping /api/version: HTTP {status} in {version_wall:.2f}s")

    cold = generate("COLD START (first /api/generate after idle)")
    print_result(cold)

    warm = generate("WARM START (immediate second /api/generate)")
    print_result(warm)

    warm2 = generate("WARM START #2 (third request, same session)")
    print_result(warm2)

    summary = {
        "endpoint": ENDPOINT,
        "model": MODEL,
        "cold_wall_seconds": round(cold.wall_seconds, 2),
        "cold_load_seconds": round(cold.load_seconds, 2) if cold.load_seconds else None,
        "warm_wall_seconds": round(warm.wall_seconds, 2),
        "warm_load_seconds": round(warm.load_seconds, 2) if warm.load_seconds else None,
        "warm2_wall_seconds": round(warm2.wall_seconds, 2),
    }
    print("\n=== SUMMARY (JSON) ===")
    print(json.dumps(summary, indent=2))

    if cold.http_status != 200 or warm.http_status != 200:
        sys.exit(1)


if __name__ == "__main__":
    main()
