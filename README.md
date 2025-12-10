# Deploy Ollama on Modal

This is derived from @irfansharif's [ollama-modal](https://github.com/irfansharif/ollama-modal) repository.
Thank you @irfansharif for the great work!

I have modified it to be an OpenAI-compatible endpoint that allows [llamabot](https://github.com/ericmjl/llamabot) to connect to the modal endpoint seamlessly.
It supports streaming and non-streaming responses.

To deploy the app, run the following command:

```bash
pixi run deploy
```

Alternatively, you can deploy directly with Modal:

```bash
# Deploy to production (main environment)
modal deploy endpoint.py

# Deploy to test environment
modal deploy endpoint.py --env test
```

To pull a new model, run:

```bash
# Pull model in production
modal run endpoint.py::OllamaService.pull_model --model-name "model-name-on-ollama-goes-here"

# Pull model in test environment
modal run endpoint.py::OllamaService.pull_model --model-name "model-name-on-ollama-goes-here" --env test
```

**Note:** Large models (like 70B) may take a while to download. The timeout has been set to 1 hour to accommodate large model downloads.

Once it's up, you can change your Ollama endpoint from `localhost:11434` to `https://<your-modal-app-prefix>.modal.run` in your relevant apps (e.g. OpenWebUI).

With LiteLLM (and LlamaBot, by extension), you can connect using a different `api_base`:

```python
import llamabot as lmb


bot = lmb.SimpleBot(
    "You are a helpful assistant.",
    model_name="ollama_chat/llama3.2",
    api_base="https://<your-modal-app-prefix>.modal.run", # no trailing slash!
)

bot("Hello!")
```

Remember, do NOT put a trailing `/` at the end, otherwise it's going to error out!

## CI/CD

This repository includes a CI/CD pipeline that automatically:

- Deploys to Modal test environment on push/PR
- Runs integration tests using llamabot SimpleBot
- Verifies GPU routing (when implemented)

See [docs/ci-cd-setup.md](docs/ci-cd-setup.md) for setup instructions.

## Documentation

- [Deployment Guide](docs/deployment-guide.md) - How to deploy and configure the service
- [CI/CD Setup](docs/ci-cd-setup.md) - Setting up automated testing
- [Scaling Configuration](docs/scaling-configuration.md) - GPU and scaling settings
- [Project Structure](docs/project-structure.md) - Codebase organization

## Current Status

- ✅ Basic Ollama service deployment on Modal (H100 GPU)
- ✅ CI/CD pipeline with test environment
- 🚧 GPU-based routing (planned - see [issue #1](https://github.com/ericmjl/ollama-on-modal/issues/1))
