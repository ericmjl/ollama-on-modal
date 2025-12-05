# AGENTS.md - Essential Commands and Knowledge

This document contains essential commands, patterns, and knowledge learned during development and troubleshooting of this project.

## Deployment Commands

### Deploy the Application
```bash
# Using pixi (recommended)
pixi run deploy

# Direct Modal deployment
modal deploy endpoint.py
```

### Update Dependencies
```bash
# Update a specific package
pixi update modal

# Install/update all dependencies
pixi install
```

### Check Installed Versions
```bash
# Check Modal version
pixi run python -c "import modal; print(modal.__version__)"

# Check Python version
pixi run python --version
```

## Git History Investigation

### View File History
```bash
# View commit history for a specific file
git log --oneline --all -- <file>

# View detailed history with diffs
git log --all -p -- <file>

# Follow file renames
git log --all --full-history --follow -- "*pattern*"
```

### Find When Files Were Added/Deleted
```bash
# Find when a file was added
git log --all --oneline --diff-filter=A -- <file>

# Find when a file was deleted
git log --all --oneline --diff-filter=D -- "*pattern*"
```

### View File at Specific Commit
```bash
# View file contents at a specific commit
git show <commit-hash>:<file-path>

# View commit details
git show <commit-hash> --stat
```

### Search Git History
```bash
# Search for commits affecting multiple files
git log --all --oneline -- <file1> <file2>

# Search for commits with specific message
git log --all --grep="deploy"
```

## Modal API Reference

### Check Modal API Documentation
```bash
# View help for @app.cls decorator
pixi run python -c "import modal; help(modal.App.cls)"
```

### Key Modal Parameters for @app.cls()

**Scaling Parameters:**
- `scaledown_window`: Seconds before idle containers are terminated (default: 60)
- `container_idle_timeout`: Alternative parameter for idle timeout
- `min_containers`: Minimum number of containers to keep running
- `max_containers`: Maximum number of containers to scale up to
- `buffer_containers`: Number of extra containers to keep ready
- `keep_warm`: Number of containers to keep warm (always running)

**Resource Parameters:**
- `gpu`: GPU configuration - use string format: `gpu="H100"` (not `modal.gpu.H100()`)
- `cpu`: CPU allocation
- `memory`: Memory allocation
- `volumes`: Dictionary mapping paths to Volume objects
- `network_file_systems`: Network file system mounts

**Other Parameters:**
- `image`: Custom image configuration
- `env`: Environment variables
- `secrets`: Modal secrets
- `timeout`: Function timeout in seconds
- `startup_timeout`: Container startup timeout

### Example Configuration
```python
@app.cls(
    volumes={"/usr/share/ollama/.ollama/models": volume},
    gpu="H100",
    scaledown_window=10,  # Scale down after 10 seconds of inactivity
    min_containers=0,
    max_containers=5,
)
class OllamaService:
    # ...
```

## Common Issues and Solutions

### Modal Version Too Old
**Error**: `The client version (0.67.18) is too old. Please update`

**Solution**:
```bash
# Update pixi.toml to allow newer versions
# Change: modal = ">=0.67.18, <0.68"
# To: modal = ">=0.67.18"

# Then update
pixi update modal
```

### Invalid Parameter Error
**Error**: `TypeError: _App.cls() got an unexpected keyword argument 'scaledown_window'`

**Solution**:
- Check Modal version - `scaledown_window` requires Modal 1.2.4+
- Update Modal: `pixi update modal`

### Deprecated GPU Format
**Warning**: `gpu=H100(...) is deprecated. Use gpu="H100" instead`

**Solution**: Use string format instead of object format
```python
# Old (deprecated)
gpu=modal.gpu.H100()

# New (correct)
gpu="H100"
```

## File Management

### Create Documentation Structure
```bash
# Create docs directory
mkdir -p docs

# Documentation files should use kebab-case naming
# Examples:
# - deployment-guide.md
# - fixing-deployment-issues.md
# - scaling-configuration.md
```

### Check for Linter Errors
```bash
# If using a linter, check specific files
# (This depends on your linter setup)
```

## Project-Specific Knowledge

### File Structure
- **`endpoint.py`**: Main deployment file (use this)
- **`pixi.toml`**: Dependency and task management
- **`ollama.service`**: Systemd service configuration
- **`docs/`**: Documentation directory (kebab-case filenames)

### Deployment Flow
```
pixi.toml (deploy task)
    ↓
endpoint.py (Modal app definition)
    ↓
Modal Cloud (deployed service)
```

### Key Configuration Values
- **GPU**: H100
- **Scale-down window**: 10 seconds (configurable)
- **Port**: 11434 (Ollama default)
- **Volume mount**: `/usr/share/ollama/.ollama/models`
- **Python version**: 3.12

## Useful Modal Commands

### Pull a Model
```bash
# Pull a model using modal run command
modal run endpoint.py::OllamaService.pull_model --model-name gemma3n:latest

# Or pull any other model
modal run endpoint.py::OllamaService.pull_model --model-name llama3.1
```

### Lookup and Interact with Deployed App
```python
import modal

# Lookup deployed app
app = modal.App.lookup("ollama-service")

# Access class instance
service = app.OllamaService()

# Call remote methods
service.pull_model.remote("llama3.1")
```

### Update Autoscaler Dynamically
```python
# Update scaling settings without redeploying
service.update_autoscaler(scaledown_window=300)
```

## Documentation Resources

- [Modal Scaling Guide](https://modal.com/docs/guide/scale)
- [Modal API Reference - @app.cls](https://modal.com/docs/reference/modal.App#modal.App.cls)
- [Modal Deployment Guide](https://modal.com/docs/guide/managing-deployments)

## Quick Reference

### Most Common Commands
```bash
# Deploy
pixi run deploy

# Update Modal
pixi update modal

# Check Modal version
pixi run python -c "import modal; print(modal.__version__)"

# View file git history
git log --oneline --all -- <file>
```

### Most Important Modal Parameters
- `scaledown_window`: Control when containers scale down (cost optimization)
- `gpu`: GPU type (use string format: `"H100"`)
- `volumes`: Persistent storage for model weights

