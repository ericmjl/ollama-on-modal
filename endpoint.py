import subprocess
import time

import modal

image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("curl", "systemctl", "zstd")
    .run_commands(
        "mkdir -p /opt/ollama && curl -fsSL https://github.com/ollama/ollama/releases/download/v0.23.1/ollama-linux-amd64.tar.zst | zstd -d | tar -x -C /opt/ollama",
        force_build=True,
    )
    .pip_install("httpx", "loguru", "fastapi")
    .env(
        {
            "OLLAMA_HOST": "0.0.0.0:11434",
            "OLLAMA_MODELS": "/usr/share/ollama/.ollama/models",
            "PATH": "/opt/ollama/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        }
    )
)

volume = modal.Volume.from_name("ollama-model-weights", create_if_missing=True)

app = modal.App(name="ollama-service", image=image)

# Model-to-GPU mapping configuration
MODEL_GPU_MAPPING = {
    # Text models
    "deepseek-r1:32b": "H100",
    "llama3.2": "A10",
    "llama3.2:1b": "A10",
    "llama3.2:3b": "A10",
    # Image generation - budget tier (A10, 24GB)
    "x/flux2-klein": "A10",
    "x/flux2-klein:4b": "A10",
    "x/z-image-turbo": "A10",
    "x/z-image-turbo:fp8": "A10",
    # Image generation - performance tier (L40S, 48GB)
    "x/flux2-klein:9b": "L40S",
    "x/z-image-turbo:bf16": "L40S",
    # Add more model mappings as needed
}


def get_gpu_for_model(model_name: str) -> str:
    """Determine which GPU service should handle a given model.

    Args:
        model_name: Name of the model (exact match required)

    Returns:
        GPU tier name (with fallbacks configured per class)

    Raises:
        ValueError: If model is not found in MODEL_GPU_MAPPING
    """
    if model_name not in MODEL_GPU_MAPPING:
        raise ValueError(
            f"Model '{model_name}' not found in MODEL_GPU_MAPPING. "
            f"Available models: {list(MODEL_GPU_MAPPING.keys())}"
        )
    return MODEL_GPU_MAPPING[model_name]


OLLAMA_BIN = "/opt/ollama/bin/ollama"
MODELS_DIR = "/usr/share/ollama/.ollama/models"


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


def _start_ollama_server() -> None:
    """Start Ollama in the background and ensure the models directory exists."""
    import os

    os.makedirs(MODELS_DIR, exist_ok=True)
    subprocess.Popen([OLLAMA_BIN, "serve"])


@app.cls(
    volumes={MODELS_DIR: volume},
    gpu=["H100", "H200", "A100-80GB"],
    scaledown_window=120,
    timeout=3600,
)
class OllamaServiceH100:
    @modal.enter()
    def enter(self):
        _start_ollama_server()

    @modal.method()
    def pull_model(self, model_name: str):
        wait_for_ollama()
        subprocess.run(["echo", "pulling model", model_name])
        subprocess.run([OLLAMA_BIN, "pull", model_name])

    @modal.method()
    def list(self):
        wait_for_ollama()
        result = subprocess.run([OLLAMA_BIN, "list"], capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
        return result.stdout

    @modal.web_server(11434, startup_timeout=300)
    def server(self):
        pass


@app.cls(
    volumes={MODELS_DIR: volume},
    gpu=["A10", "L4", "T4"],
    scaledown_window=120,
    timeout=3600,
)
class OllamaServiceA10:
    @modal.enter()
    def enter(self):
        _start_ollama_server()

    @modal.method()
    def pull_model(self, model_name: str):
        wait_for_ollama()
        subprocess.run(["echo", "pulling model", model_name])
        subprocess.run([OLLAMA_BIN, "pull", model_name])

    @modal.method()
    def list(self):
        wait_for_ollama()
        result = subprocess.run([OLLAMA_BIN, "list"], capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
        return result.stdout

    @modal.web_server(11434, startup_timeout=300)
    def server(self):
        pass


@app.cls(
    volumes={MODELS_DIR: volume},
    gpu=["L40S", "A100-40GB", "A100-80GB"],
    scaledown_window=120,
    timeout=3600,
)
class OllamaServiceL40S:
    @modal.enter()
    def enter(self):
        _start_ollama_server()

    @modal.method()
    def pull_model(self, model_name: str):
        wait_for_ollama()
        subprocess.run(["echo", "pulling model", model_name])
        subprocess.run([OLLAMA_BIN, "pull", model_name])

    @modal.method()
    def list(self):
        wait_for_ollama()
        result = subprocess.run([OLLAMA_BIN, "list"], capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
        return result.stdout

    @modal.web_server(11434, startup_timeout=300)
    def server(self):
        pass


@app.cls()
@modal.concurrent(max_inputs=100)
class OllamaPassthrough:
    @modal.enter()
    def enter(self):
        import httpx

        self.http_client = httpx.AsyncClient(timeout=300.0)

    @modal.exit()
    async def exit(self):
        await self.http_client.aclose()

    async def _get_model_name(self, request) -> str | None:
        """Extract model name from request body. Simple and minimal."""
        try:
            body = await request.json()
            return body.get("model") or body.get("name")
        except Exception:
            return None

    def _get_service_url(self, gpu_type: str, base_url: str | None = None) -> str:
        """Get internal Modal URL for GPU service.

        Args:
            gpu_type: "H100", "A10", or "L40S"
            base_url: Optional base URL to construct service URL from
        """
        class_map = {
            "H100": "ollamaserviceh100",
            "A10": "ollamaservicea10",
            "L40S": "ollamaservicel40s",
        }
        class_name = class_map.get(gpu_type, "ollamaserviceh100")

        if base_url:
            base = base_url.replace("ollamapassthrough-server", "")
            return f"{base}{class_name}-server.modal.run"
        import os

        env = os.environ.get("MODAL_ENVIRONMENT", "main")
        env_suffix = f"{env}-" if env and env != "main" else ""
        username = "ericmjl"
        return (
            f"https://{username}-{env_suffix}--ollama-service-{class_name}-server.modal.run"
        )

    @modal.asgi_app()
    def web_app(self):
        import fastapi
        from fastapi.responses import StreamingResponse

        app_fastapi = fastapi.FastAPI()
        http_client = self.http_client

        @app_fastapi.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
        async def passthrough(path: str, request: fastapi.Request):
            """Simple passthrough: extract model, forward request."""
            model_name = await self._get_model_name(request)
            base_url = str(request.url).replace(request.url.path, "")

            if model_name:
                try:
                    gpu_type = get_gpu_for_model(model_name)
                    service_url = self._get_service_url(gpu_type, base_url)
                except ValueError as e:
                    return fastapi.Response(content=str(e), status_code=400)
            else:
                service_url = self._get_service_url("H100", base_url)

            target_url = f"{service_url}/{path}"
            body = await request.body()

            response = await http_client.request(
                method=request.method,
                url=target_url,
                headers=dict(request.headers),
                params=dict(request.query_params),
                content=body,
            )

            if "stream" in request.query_params:
                return StreamingResponse(
                    response.aiter_bytes(),
                    status_code=response.status_code,
                    headers=dict(response.headers),
                )

            return fastapi.Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers),
            )

        return app_fastapi
