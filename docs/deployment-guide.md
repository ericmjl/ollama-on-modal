# Deployment Guide

This guide explains how to deploy the Ollama service on Modal.

## Quick Start

Deploy the service to production (main environment):

```bash
pixi run deploy
```

Or directly with Modal:

```bash
modal deploy endpoint.py
```

Deploy to test environment:

```bash
modal deploy endpoint.py --env test
```

## What Gets Deployed

The deployment uses `endpoint.py`, which:

- Sets up an Ollama service on Modal with H100 GPU
- Mounts a persistent volume for model weights at `/usr/share/ollama/.ollama/models`
- Exposes the Ollama API on port 11434
- Automatically starts the Ollama service when the container initializes

## Deployment Output

After successful deployment, you'll receive:

- **Web endpoint URL**:
  - Production (main): `https://ericmjl--ollama-service-ollamaservice-server.modal.run`
  - Test: `https://ericmjl-test--ollama-service-ollamaservice-server.modal.run`
- **Modal dashboard link**:
  - Production: `https://modal.com/apps/ericmjl/main/deployed/ollama-service`
  - Test: `https://modal.com/apps/ericmjl/test/deployed/ollama-service`

**Note**: The endpoint URL format is:
`https://{username}-{env-suffix}--{app-name}-{class-name}-{method-name}.modal.run`

Where `{env-suffix}` is empty for main environment, or the environment name
(e.g., "test") for other environments.

## Configuration

The service is configured with:

- **GPU**: H100 (configurable in `endpoint.py`)
- **Volume**: Persistent storage for model weights
- **Port**: 11434 (Ollama's default API port)
- **Environment**: Python 3.12 on Debian slim

## Environments

Modal supports multiple environments for deploying the same app:

- **Main/Production**: Default environment (`modal deploy endpoint.py`)
- **Test**: Separate environment for testing (`modal deploy endpoint.py --env test`)

Both environments use the same app name (`ollama-service`) but are isolated:

- Separate secrets and configuration
- Separate volumes and resources
- Different endpoint URLs

## Pulling Models

To pull a model, you can use the `pull_model` method:

```python
import modal

# For production (main environment)
app = modal.App.lookup("ollama-service")
service = app.OllamaService()
service.pull_model.remote("llama3.1")

# For test environment
app = modal.App.lookup("ollama-service", environment="test")
service = app.OllamaService()
service.pull_model.remote("llama3.1")
```

Or use the Ollama API directly via the web endpoint, or via pixi tasks:

```bash
# Pull model in production
pixi run pull-model llama3.1
# Or: modal run endpoint.py::OllamaService.pull_model --model-name llama3.1

# Pull test models (test environment)
pixi run pull-test-models  # Pulls both H100 and A10G test models
pixi run pull-test-model-h100  # Pulls deepseek-r1:32b
pixi run pull-test-model-a10g  # Pulls llama3.2
# Or: modal run --env test endpoint.py::OllamaService.pull_model --model-name llama3.1
```
