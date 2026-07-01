"""vLLM serving endpoint for Qwen3.6-27B (AWQ-INT4) on Modal.

Uses vLLM sleep mode + Modal GPU snapshots for fast cold starts: the model is
loaded and snapshotted once; subsequent containers restore from snapshot and
just wake the model back onto the GPU. This is the key advantage over the
Ollama deployment (whose subprocess GPU state doesn't survive snapshot/restore).
"""

import json
import socket
import subprocess
from typing import Any

import aiohttp
import modal

MINUTES = 60
VLLM_PORT = 8000

MODEL_NAME = "cyankiwi/Qwen3.6-27B-AWQ-INT4"
SERVED_NAME = "qwen3.6-27b"
N_GPU = 1

app = modal.App("qwen36-vllm-service")

vllm_image = (
    modal.Image.from_registry(
        "nvidia/cuda:12.9.0-devel-ubuntu22.04", add_python="3.12"
    )
    .entrypoint([])
    .uv_pip_install("vllm", "hf_transfer")
    .env(
        {
            "HF_XET_HIGH_PERFORMANCE": "1",
            "HF_HUB_ENABLE_HF_TRANSFER": "1",
            "TORCHINDUCTOR_COMPILE_THREADS": "1",
            "TORCHINDUCTOR_CACHE_DIR": "/tmp/torchinductor",
        }
    )
)

hf_cache_vol = modal.Volume.from_name("huggingface-cache", create_if_missing=True)
vllm_cache_vol = modal.Volume.from_name("vllm-cache", create_if_missing=True)

with vllm_image.imports():
    import requests


def wait_ready(proc: subprocess.Popen):
    while True:
        try:
            socket.create_connection(("localhost", VLLM_PORT), timeout=1).close()
            return
        except OSError:
            if proc.poll() is not None:
                raise RuntimeError(f"vLLM exited with {proc.returncode}")


def warmup():
    payload = {
        "model": SERVED_NAME,
        "messages": [{"role": "user", "content": "warmup"}],
        "max_tokens": 16,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    for _ in range(3):
        requests.post(
            f"http://localhost:{VLLM_PORT}/v1/chat/completions",
            json=payload,
            timeout=300,
        ).raise_for_status()


def sleep(level=1):
    requests.post(f"http://localhost:{VLLM_PORT}/sleep?level={level}").raise_for_status()


def wake_up():
    requests.post(f"http://localhost:{VLLM_PORT}/wake_up").raise_for_status()


@app.cls(
    image=vllm_image,
    gpu="L40S",
    scaledown_window=2 * MINUTES,
    timeout=20 * MINUTES,
    volumes={
        "/root/.cache/huggingface": hf_cache_vol,
    },
    enable_memory_snapshot=True,
    experimental_options={"enable_gpu_snapshot": True},
)
@modal.concurrent(max_inputs=32)
class VllmServer:
    @modal.enter(snap=True)
    def start(self):
        cmd = [
            "vllm",
            "serve",
            MODEL_NAME,
            "--served-model-name",
            SERVED_NAME,
            "--host",
            "0.0.0.0",
            "--port",
            str(VLLM_PORT),
            "--uvicorn-log-level=info",
            "--tensor-parallel-size",
            str(N_GPU),
            "--enable-sleep-mode",
            "--max-num-seqs",
            "8",
            "--max-model-len",
            "32768",
            "--max-num-batched-tokens",
            "8192",
            "--gpu-memory-utilization",
            "0.90",
            "--dtype",
            "auto",
            "--reasoning-parser",
            "qwen3",
            "--language-model-only",
        ]

        print(*cmd)

        self.vllm_proc = subprocess.Popen(cmd)

        wait_ready(self.vllm_proc)

        warmup()

    @modal.enter(snap=False)
    def restore(self):
        wait_ready(self.vllm_proc)

    @modal.web_server(port=VLLM_PORT, startup_timeout=20 * MINUTES)
    def serve(self):
        pass

    @modal.exit()
    def stop(self):
        self.vllm_proc.terminate()


@app.local_entrypoint()
async def test(content=None):
    url = await VllmServer().serve.get_web_url.aio()

    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": content or "What is the capital of France?"},
    ]

    async with aiohttp.ClientSession(base_url=url) as session:
        print(f"Health check for {url}")
        async with session.get("/health", timeout=10 * MINUTES) as resp:
            assert resp.status == 200, f"health check failed: {resp.status}"
        print("Health OK. Sending request:")

        payload: dict[str, Any] = {
            "messages": messages,
            "model": SERVED_NAME,
            "stream": True,
            "max_tokens": 256,
            "chat_template_kwargs": {"enable_thinking": False},
        }
        headers = {"Content-Type": "application/json", "Accept": "text/event-stream"}
        async with session.post(
            "/v1/chat/completions", json=payload, headers=headers
        ) as resp:
            async for raw in resp.content:
                resp.raise_for_status()
                line = raw.decode().strip()
                if not line or line == "data: [DONE]":
                    continue
                if line.startswith("data: "):
                    line = line[len("data: ") :]
                chunk = json.loads(line)
                delta = chunk["choices"][0]["delta"]
                content_text = (
                    delta.get("content")
                    or delta.get("reasoning")
                    or delta.get("reasoning_content")
                )
                if content_text:
                    print(content_text, end="")
    print()
