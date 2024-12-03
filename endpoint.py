import modal
import os
import subprocess
import time
from fastapi import FastAPI, Request, HTTPException
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


MODEL = os.environ.get("MODEL", "qwq")

DEFAULT_MODELS = ["qwq"]


def pull():
    subprocess.run(["systemctl", "daemon-reload"])
    subprocess.run(["systemctl", "enable", "ollama"])
    subprocess.run(["systemctl", "start", "ollama"])
    wait_for_ollama()
    subprocess.run(["ollama", "pull", MODEL], stdout=subprocess.PIPE)


def wait_for_ollama(timeout: int = 30, interval: int = 2) -> None:
    """Wait for Ollama service to be ready.

    :param timeout: Maximum time to wait in seconds
    :param interval: Time between checks in seconds
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


image = (
    modal.Image.debian_slim()
    .apt_install("curl", "systemctl")
    .run_commands(  # from https://github.com/ollama/ollama/blob/main/docs/linux.md
        "curl -L https://ollama.com/download/ollama-linux-amd64.tgz -o ollama-linux-amd64.tgz",
        "tar -C /usr -xzf ollama-linux-amd64.tgz",
        "useradd -r -s /bin/false -U -m -d /usr/share/ollama ollama",
        "usermod -a -G ollama $(whoami)",
    )
    .copy_local_file("ollama.service", "/etc/systemd/system/ollama.service")
    .pip_install("ollama", "httpx", "loguru")
    .run_function(pull)
)
app = modal.App(name="ollama", image=image)
api = FastAPI()


class ChatMessage(BaseModel):
    role: str = Field(
        ..., description="The role of the message sender (e.g. 'user', 'assistant')"
    )
    content: str = Field(..., description="The content of the message")


class ChatCompletionRequest(BaseModel):
    model: Optional[str] = Field(
        default=MODEL, description="The model to use for completion"
    )
    messages: List[ChatMessage] = Field(
        ..., description="The messages to generate a completion for"
    )


@api.post("/v1/chat/completions")
async def v1_chat_completions(request: ChatCompletionRequest) -> Dict[str, Any]:
    """Handle chat completion requests in OpenAI-compatible format.

    :param request: Chat completion parameters
    :return: Chat completion response in OpenAI-compatible format
    :raises HTTPException: If the request is invalid or processing fails
    """
    import ollama  # Import here to ensure it's available in the Modal container

    try:
        if not request.messages:
            raise HTTPException(
                status_code=400,
                detail="Messages array is required and cannot be empty",
            )

        response = ollama.chat(
            model=request.model, messages=[msg.dict() for msg in request.messages]
        )

        return {
            "id": "chat-" + str(int(time.time())),
            "object": "chat.completion",
            "created": int(time.time()),
            "model": request.model,
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": response["message"]["content"],
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": -1,  # Ollama doesn't provide token counts
                "completion_tokens": -1,
                "total_tokens": -1,
            },
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error processing chat completion: {str(e)}"
        )


@app.cls(
    gpu=modal.gpu.A10G(count=1),
    container_idle_timeout=10,
)
class Ollama:
    def __init__(self):
        self.serve()

    @modal.build()
    def build(self):
        subprocess.run(["systemctl", "daemon-reload"])
        subprocess.run(["systemctl", "enable", "ollama"])

    @modal.enter()
    def enter(self):
        subprocess.run(["systemctl", "start", "ollama"])
        wait_for_ollama()
        subprocess.run(["ollama", "pull", MODEL])

    @modal.asgi_app()
    def serve(self):
        return api
