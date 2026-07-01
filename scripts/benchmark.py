# /// script
# dependencies = ["httpx", "matplotlib", "numpy"]
# ///
"""Benchmark Ollama vs vLLM vs SGLang deployments of Qwen3.6-27B on Modal.

Runs N warm requests per engine, saves raw data to JSON, and generates
a comparison plot showing every data point.

Usage:
    uv run scripts/benchmark.py                     # 6 warm runs + plot
    uv run scripts/benchmark.py --runs 10            # more runs
    uv run scripts/benchmark.py --no-plot            # skip plotting
"""

import argparse
import json
import time
from datetime import datetime
from pathlib import Path

import httpx

ENDPOINTS = {
    "Ollama\n(Q4_K_M)": {
        "url": "https://ericmjl--ollama-service-ollamaservice-server.modal.run/v1/chat/completions",
        "model": "qwen3.6:27b",
    },
    "vLLM\n(AWQ-INT4)": {
        "url": "https://ericmjl--qwen36-vllm-service-vllmserver-serve.modal.run/v1/chat/completions",
        "model": "qwen3.6-27b",
    },
    "SGLang\n(AWQ-INT4)": {
        "url": "https://ericmjl--sglang-service-sglangserver-serve.modal.run/v1/chat/completions",
        "model": "qwen3.6-27b",
    },
}

PROMPT = "Explain how gradient descent works in three concise sentences."
MAX_TOKENS = 300
OUTPUT_DIR = Path(__file__).parent.parent / "benchmark_results"


def stream_request(url: str, model: str, *, timeout: float = 600) -> dict:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": PROMPT}],
        "max_tokens": MAX_TOKENS,
        "stream": True,
        "temperature": 0.0,
    }

    t_request = time.perf_counter()
    ttft = None
    token_count = 0
    first_token_time = None

    with httpx.Client(timeout=timeout, follow_redirects=True) as client:
        with client.stream("POST", url, json=payload) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line or not line.startswith("data: "):
                    continue
                data = line[len("data: ") :]
                if data == "[DONE]":
                    break
                try:
                    chunk = json.loads(data)
                except json.JSONDecodeError:
                    continue
                choices = chunk.get("choices") or []
                if choices:
                    delta = choices[0].get("delta", {})
                    content = (
                        delta.get("content")
                        or delta.get("reasoning")
                        or delta.get("reasoning_content")
                    )
                    if content:
                        if ttft is None:
                            ttft = time.perf_counter() - t_request
                            first_token_time = time.perf_counter()
                        token_count += 1
                usage = chunk.get("usage")
                if usage and usage.get("completion_tokens"):
                    token_count = usage["completion_tokens"]

    t_end = time.perf_counter()
    total = t_end - t_request
    gen_time = (t_end - first_token_time) if first_token_time else total
    tps = token_count / gen_time if gen_time > 0 else 0.0

    return {
        "ttft": ttft if ttft is not None else total,
        "total": total,
        "tokens": token_count,
        "tps": tps,
    }


def warmup(url: str, model: str) -> bool:
    try:
        stream_request(url, model, timeout=120)
        return True
    except Exception as exc:
        print(f"    warmup failed: {exc}")
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", type=int, default=6, help="warm runs per endpoint")
    ap.add_argument("--no-plot", action="store_true")
    args = ap.parse_args()

    all_results: dict[str, list[dict]] = {}

    print("=" * 78)
    print(f"WARM PERFORMANCE — {args.runs} runs per engine")
    print(f"  prompt: {PROMPT[:60]}...  max_tokens={MAX_TOKENS}")
    print("=" * 78)

    for name, cfg in ENDPOINTS.items():
        label = name.replace("\n", " ")
        print(f"\n[{label}]  warming up...")
        if not warmup(cfg["url"], cfg["model"]):
            print(f"[{label}]  SKIPPED (warmup failed)")
            continue
        print(f"[{label}]  measuring {args.runs} runs:")
        runs = []
        for i in range(args.runs):
            r = stream_request(cfg["url"], cfg["model"])
            runs.append(r)
            all_results[name] = runs
            print(
                f"  run {i+1}: ttft={r['ttft']:.3f}s  "
                f"tps={r['tps']:.1f}  tokens={r['tokens']}  total={r['total']:.2f}s"
            )

    # save raw data
    OUTPUT_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = OUTPUT_DIR / f"benchmark_{timestamp}.json"
    with open(json_path, "w") as f:
        json.dump(
            {
                "timestamp": timestamp,
                "prompt": PROMPT,
                "max_tokens": MAX_TOKENS,
                "runs": args.runs,
                "results": all_results,
            },
            f,
            indent=2,
        )
    print(f"\nRaw data saved to {json_path}")

    # summary table
    print("\n" + "=" * 78)
    print("SUMMARY (median across runs)")
    print("=" * 78)
    for name, runs in all_results.items():
        if not runs:
            continue
        ttfts = sorted(r["ttft"] for r in runs)
        tps_list = sorted(r["tps"] for r in runs)
        totals = sorted(r["total"] for r in runs)
        n = len(ttfts)
        med = lambda v: v[n // 2]
        print(
            f"  {name.replace(chr(10), ' '):<24} "
            f"ttft={med(ttfts):.3f}s  "
            f"tps={med(tps_list):.1f}  "
            f"total={med(totals):.2f}s  "
            f"(n={n})"
        )
    print()

    if not args.no_plot and all_results:
        plot_results(all_results, json_path)


def plot_results(data: dict[str, list[dict]], json_path: Path):
    import matplotlib.pyplot as plt
    import numpy as np

    engines = [k for k, v in data.items() if v]
    metrics = [
        ("ttft", "Time to first token (s)", "TTFT"),
        ("tps", "Tokens / second", "Throughput"),
        ("total", "Total latency (s)", "Total"),
    ]
    colors = {"Ollama\n(Q4_K_M)": "#4C72B0", "vLLM\n(AWQ-INT4)": "#55A868", "SGLang\n(AWQ-INT4)": "#C44E52"}

    fig, axes = plt.subplots(1, 3, figsize=(14, 5))
    fig.suptitle(
        "Qwen3.6-27B on Modal: Ollama vs vLLM vs SGLang\n"
        f"Same L40S GPU, 4-bit quant, {PROMPT[:40]}...",
        fontsize=12,
        fontweight="bold",
    )

    for ax, (key, ylabel, title) in zip(axes, metrics):
        positions = []
        all_vals = []
        for i, eng in enumerate(engines):
            vals = [r[key] for r in data[eng]]
            all_vals.append(vals)
            positions.append(i)
            jitter = np.random.uniform(-0.12, 0.12, len(vals))
            color = colors.get(eng, "#888888")
            ax.scatter(
                [i + j for j in jitter], vals, color=color, s=60, alpha=0.7, zorder=3, edgecolors="white", linewidths=0.5
            )
            med = sorted(vals)[len(vals) // 2]
            ax.plot([i - 0.2, i + 0.2], [med, med], color=color, linewidth=2.5, zorder=2)

        ax.set_xticks(range(len(engines)))
        ax.set_xticklabels([e.replace("\n", " ") for e in engines], fontsize=9)
        ax.set_ylabel(ylabel, fontsize=10)
        ax.set_title(title, fontsize=11)
        ax.set_xlim(-0.5, len(engines) - 0.5)
        ax.grid(axis="y", alpha=0.3)

    plt.tight_layout()
    plot_path = json_path.with_suffix(".png")
    fig.savefig(plot_path, dpi=150, bbox_inches="tight")
    print(f"Plot saved to {plot_path}")


if __name__ == "__main__":
    main()
