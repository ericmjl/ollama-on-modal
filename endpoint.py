import subprocess
import time

import modal

DEFAULT_MODEL = "qwen3.6:35b"

image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("curl", "systemctl", "zstd")
    .run_commands("curl -fsSL https://ollama.com/install.sh | sh", force_build=False)
    .pip_install("httpx", "loguru")
    .env(
        {
            "OLLAMA_HOST": "0.0.0.0:11434",
            "OLLAMA_MODELS": "/usr/share/ollama/.ollama/models",
            # Keep weights in GPU memory while the container is alive (including at snapshot time).
            "OLLAMA_KEEP_ALIVE": "-1",
        }
    )
)

volume = modal.Volume.from_name("ollama-model-weights", create_if_missing=True)

app = modal.App(name="ollama-service", image=image)


def wait_for_ollama(timeout: int = 120, interval: int = 2) -> None:
    """Wait for Ollama service to be ready.

    :param timeout: Maximum time to wait in seconds
    :param interval: Time between checks in seconds
    :raises TimeoutError: If the service doesn't start within the timeout period
    """
    import httpx
    from loguru import logger

    start_time = time.time()
    while True:
        try:
            response = httpx.get(
                "http://localhost:11434/api/version", timeout=interval + 3
            )
            if response.status_code == 200:
                logger.info("Ollama service is ready")
                return
        except (httpx.ConnectError, httpx.ReadTimeout, httpx.TimeoutException):
            if time.time() - start_time > timeout:
                raise TimeoutError("Ollama service failed to start")
            logger.info(
                f"Waiting for Ollama service... ({int(time.time() - start_time)}s)"
            )
            time.sleep(interval)


def warmup_model(model_name: str = DEFAULT_MODEL, timeout: float = 600.0) -> None:
    """Load model weights into GPU VRAM before taking a memory snapshot."""
    import httpx
    from loguru import logger

    logger.info(f"Warming up {model_name} for GPU snapshot...")
    response = httpx.post(
        "http://localhost:11434/api/generate",
        json={"model": model_name, "prompt": "warmup", "stream": False},
        timeout=timeout,
    )
    response.raise_for_status()
    logger.info("Model warmup complete")


@app.cls(
    volumes={"/usr/share/ollama/.ollama/models": volume},
    gpu=["L40S", "A100-40GB"],
    scaledown_window=120,
    timeout=3600,
    enable_memory_snapshot=True,
    experimental_options={"enable_gpu_snapshot": True},
)
class OllamaService:
    @modal.enter(snap=True)
    def prepare_gpu_snapshot(self):
        """Start Ollama and load the model into GPU memory before snapshotting."""
        subprocess.Popen(["ollama", "serve"])
        wait_for_ollama(timeout=180)
        warmup_model()

    @modal.enter()
    def verify_after_restore(self):
        """Runs after snapshot restore; confirm Ollama is responding."""
        wait_for_ollama(timeout=60)

    @modal.method()
    def pull_model(self, model_name: str = DEFAULT_MODEL):
        wait_for_ollama()
        subprocess.run(["echo", "pulling model", model_name])
        subprocess.run(["ollama", "pull", model_name], check=True)

    @modal.method()
    def list(self):
        """List all available models."""
        wait_for_ollama()
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
        return result.stdout

    @modal.web_server(11434, startup_timeout=600)
    def server(self):
        pass
