import modal

OLLAMA_BIN = "/opt/ollama/bin/ollama"

image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("curl", "zstd")
    .pip_install("httpx")
    .run_commands(
        "mkdir -p /opt/ollama && curl -fsSL https://github.com/ollama/ollama/releases/download/v0.23.1/ollama-linux-amd64.tar.zst | zstd -d | tar -x -C /opt/ollama",
        force_build=True,
    )
    .env({"OLLAMA_HOST": "0.0.0.0:11434"})
)

app = modal.App(name="ollama-gpu-test", image=image)


@app.function(gpu=["A10", "L4", "T4"], timeout=600)
def test_ollama_gpu():
    import subprocess
    import time
    import httpx

    proc = subprocess.Popen(
        [OLLAMA_BIN, "serve"], stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    time.sleep(10)

    for i in range(60):
        try:
            r = httpx.get("http://localhost:11434/api/version", timeout=10)
            print(f"Ollama version: {r.json()}")
            proc.terminate()
            return "SUCCESS"
        except Exception as e:
            print(f"Attempt {i + 1}: {e}")
            time.sleep(10)

    proc.terminate()
    return "FAILED"
