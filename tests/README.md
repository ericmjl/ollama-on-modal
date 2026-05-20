# Tests

## Integration (`tests/test_endpoints.py`)

Manual checks against the deployed passthrough URL using LlamaBot and httpx:

```bash
uv run tests/test_endpoints.py
```

## Modal spikes (`tests/modal/`)

Small standalone Modal apps for debugging Ollama startup and GPU availability. Deploy or run directly, e.g.:

```bash
uvx modal run tests/modal/test_ollama.py::test_ollama
uvx modal deploy tests/modal/test_cpu.py
```
