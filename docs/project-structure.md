# Project Structure

This document explains the project structure and file purposes.

## File Overview

### `endpoint.py` ✅ (Use This)

**Status**: Active deployment file

This is the correct file to use for deployment. It contains:

- Modal app configuration for Ollama service
- H100 GPU configuration
- Persistent volume mounting for model weights
- Ollama service initialization
- Web server endpoint on port 11434

**Deployment**: Use `pixi run deploy` or `modal deploy endpoint.py`

### `router.py` ❌ (Deprecated)

**Status**: Not used for deployment

This file was a FastAPI proxy implementation but is not the correct deployment target. It has been removed from the project.

**Note**: The `pixi.toml` deploy task correctly references `endpoint.py`, not `router.py`.

### `endpoint_v2.py` (Alternative Implementation)

**Status**: Alternative implementation, not used

This file contains a simpler Ollama service implementation using `@modal.web_server()` instead of the FastAPI proxy approach. It's kept for reference but is not the active deployment target.

### `pixi.toml`

**Purpose**: Project configuration and dependency management

- Defines Python dependencies (FastAPI, loguru)
- Defines Modal version (>=0.67.18)
- Contains tasks:
  - `deploy`: Deploy to production (`modal deploy endpoint.py`)
  - `pull-model`: Pull a model in production
  - `list-models`: List available models
  - `pull-test-models`: Pull all test models (H100 + A10G)
  - `pull-test-model-h100`: Pull deepseek-r1:32b to test environment
  - `pull-test-model-a10g`: Pull llama3.2 to test environment

### `scripts/test_gpu_routing.py`

**Purpose**: Test script for GPU routing functionality

- Uses llamabot SimpleBot to test model routing
- Tests H100 and A10G model routing
- Uses inline script metadata (PEP 723) for dependencies
- Run with: `uv run scripts/test_gpu_routing.py`

### `ollama.service`

**Purpose**: Systemd service file for Ollama

This file is not currently used in the deployment. Ollama is started directly via `subprocess.Popen` in `endpoint.py`.

## Git History Context

From the git history:

1. **Original `endpoint.py`**: Was deleted in May 2025 (commit 2454872) - it was a FastAPI endpoint for chat completions
2. **`endpoint_v2.py`**: Created in April 2025 as an alternative implementation
3. **Current `endpoint.py`**: The current file is a different implementation focused on running Ollama as a service

## Deployment Flow

```text
pixi.toml (deploy task)
    ↓
endpoint.py (Modal app definition)
    ↓
Modal Cloud (deployed service)
```

## Key Configuration Files

- **`endpoint.py`**: Main deployment file - defines the Modal app
- **`pixi.toml`**: Dependency and task management
- **`ollama.service`**: Systemd service configuration (used in image build)
