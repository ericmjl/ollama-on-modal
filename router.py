import modal
import os
import subprocess
import time
from typing import List, Optional, AsyncGenerator
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse


OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "llama3.1"


def pull(model: str = DEFAULT_MODEL) -> None:
    """Pull specified model during image creation.

    :param model: Name of the model to pull from Ollama. Defaults to DEFAULT_MODEL.
    """
    subprocess.run(["systemctl", "daemon-reload"])
    subprocess.run(["systemctl", "enable", "ollama"])
    subprocess.run(["systemctl", "start", "ollama"])
    wait_for_ollama()
    subprocess.run(["ollama", "pull", model], stdout=subprocess.PIPE)


def wait_for_ollama(timeout: int = 30, interval: int = 2) -> None:
    """Wait for Ollama service to be ready."""
    from loguru import logger
    import httpx

    start_time = time.time()
    while True:
        try:
            response = httpx.get(f"{OLLAMA_BASE_URL}/api/version")
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


# Image setup remains the same
image = (
    modal.Image.debian_slim()
    .apt_install("curl", "systemctl")
    .run_commands(
        "curl -L https://ollama.com/download/ollama-linux-amd64.tgz -o ollama-linux-amd64.tgz",
        "tar -C /usr -xzf ollama-linux-amd64.tgz",
        "useradd -r -s /bin/false -U -m -d /usr/share/ollama ollama",
        "usermod -a -G ollama $(whoami)",
    )
    .copy_local_file("ollama.service", "/etc/systemd/system/ollama.service")
    .pip_install("httpx", "loguru")
    .run_function(pull)
)

app = modal.App(name="ollama", image=image)


@app.cls(
    gpu=modal.gpu.A10G(count=1),
    container_idle_timeout=300,
)
class OllamaProxy:
    def __init__(self):
        import httpx

        self.app = FastAPI()
        self.client = httpx.AsyncClient(base_url=OLLAMA_BASE_URL)
        self.setup_routes()

    def setup_routes(self):
        @self.app.api_route(
            "/api/{path:path}", methods=["GET", "POST", "DELETE", "HEAD"]
        )
        async def proxy_request(request: Request, path: str):
            """Proxy all requests to Ollama API"""
            try:
                # Get the raw body content
                body = await request.body()

                # Forward the request to Ollama
                response = await self.client.request(
                    method=request.method,
                    url=f"/api/{path}",
                    content=body,
                    headers={
                        k: v
                        for k, v in request.headers.items()
                        if k.lower() not in ["host", "content-length"]
                    },
                )

                # Handle streaming responses
                if response.headers.get("transfer-encoding") == "chunked":
                    return StreamingResponse(
                        response.iter_bytes(),
                        media_type=response.headers.get("content-type"),
                        headers={
                            k: v
                            for k, v in response.headers.items()
                            if k.lower() not in ["transfer-encoding", "content-length"]
                        },
                    )

                # Handle regular responses
                return JSONResponse(
                    content=response.json() if response.content else None,
                    status_code=response.status_code,
                    headers={
                        k: v
                        for k, v in response.headers.items()
                        if k.lower() not in ["transfer-encoding", "content-length"]
                    },
                )

            except httpx.RequestError as e:
                logger.error(f"Error proxying request: {e}")
                raise HTTPException(status_code=502, detail=str(e))
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                raise HTTPException(status_code=500, detail=str(e))

    @modal.enter()
    def enter(self):
        """Start Ollama service when container starts"""
        subprocess.run(["systemctl", "start", "ollama"])
        wait_for_ollama()

    @modal.exit()
    async def exit(self):
        """Clean up resources when container stops"""
        await self.client.aclose()

    @modal.asgi_app()
    def serve(self):
        return self.app
