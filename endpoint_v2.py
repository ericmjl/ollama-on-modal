import modal
import subprocess
import time


image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("curl", "systemctl")
    .run_commands(
        "curl -fsSL https://ollama.com/install.sh | sh",
    )
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


def wait_for_ollama(timeout: int = 30, interval: int = 2) -> None:
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
            response = httpx.get("http://localhost:11434/api/version")
            if response.status_code == 200:
                logger.info("Ollama service is ready")
                return
        except httpx.ConnectError:
            if time.time() - start_time > timeout:
                raise TimeoutError("Ollama service failed to start")
            logger.info(
                f"Waiting for Ollama service... ({int(time.time() - start_time)}s)"
            )
            time.sleep(interval)


@app.cls(
    scaledown_window=10,
    volumes={"/usr/share/ollama/.ollama/models": volume},
    memory=1024 * 1,
    gpu="A10G",
)
class OllamaService:

    @modal.enter()
    def enter(self):
        subprocess.Popen(["ollama", "serve"])

    @modal.method()
    def pull_model(self, model_name: str):
        subprocess.run(["echo", "pulling model", model_name])
        subprocess.run(["ollama", "pull", model_name])

    @modal.web_server(11434)
    def server(self):
        pass
