import modal
import os
import subprocess
import time

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


@app.cls(
    gpu=modal.gpu.A10G(count=1),
    container_idle_timeout=300,
)
class Ollama:
    @modal.build()
    def build(self):
        subprocess.run(["systemctl", "daemon-reload"])
        subprocess.run(["systemctl", "enable", "ollama"])

    @modal.enter()
    def enter(self):
        subprocess.run(["systemctl", "start", "ollama"])
        wait_for_ollama()
        subprocess.run(["ollama", "pull", MODEL])

    @modal.web_endpoint(docs=True)
    def v1_chat_completions(self, message: str, model: str = MODEL):
        import ollama

        response = ollama.chat(
            model=model, messages=[{"role": "user", "content": message}]
        )
        return response
