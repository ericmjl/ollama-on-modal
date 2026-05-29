import subprocess
import time

import modal

DEFAULT_MODEL = "qwen3.5:35b"

image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("curl", "systemctl", "zstd")
    .run_commands("curl -fsSL https://ollama.com/install.sh | sh", force_build=False)
    .pip_install("httpx", "loguru")
    .env(
        {
            "OLLAMA_HOST": "0.0.0.0:11434",
            "OLLAMA_MODELS": "/usr/share/ollama/.ollama/models",
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


@app.cls(
    volumes={"/usr/share/ollama/.ollama/models": volume},
    gpu="H100",
    scaledown_window=120,
    timeout=3600,
)
class OllamaService:
    @modal.enter()
    def enter(self):
        subprocess.Popen(["ollama", "serve"])

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

    @modal.web_server(11434, startup_timeout=300)
    def server(self):
        pass
