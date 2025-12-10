# Scaling Configuration

This document explains how to configure autoscaling and scale-down behavior for the Ollama service on Modal.

## Scale-Down Configuration

To ensure containers scale down after a period of inactivity, use the `scaledown_window` parameter in the `@app.cls()` decorator.

### Current Configuration

In `endpoint.py`, we've configured:

```python
@app.cls(
    volumes={"/usr/share/ollama/.ollama/models": volume},
    gpu="H100",
    scaledown_window=10,  # Scale down after 10 seconds of inactivity
)
```

This means containers will automatically terminate after **10 seconds** of inactivity.

### Parameter Options

Modal's `@app.cls()` decorator supports two related parameters:

1. **`scaledown_window`** (recommended): Maximum duration in seconds that containers can remain idle before being terminated
   - Default: 60 seconds
   - Example: `scaledown_window=600` (10 minutes)

2. **`container_idle_timeout`**: Alternative parameter with similar behavior
   - Note: `scaledown_window` is the preferred parameter in newer Modal versions

### Choosing the Right Value

Consider these factors when setting `scaledown_window`:

- **Lower values (e.g., 60-300 seconds)**:
  - ✅ Lower costs (containers terminate quickly)
  - ❌ More cold starts (slower response for intermittent traffic)

- **Higher values (e.g., 600-1800 seconds)**:
  - ✅ Fewer cold starts (faster response for intermittent traffic)
  - ❌ Higher costs (containers stay alive longer)

### Example Configurations

**Cost-optimized** (scale down quickly):

```python
@app.cls(
    scaledown_window=60,  # 1 minute
    # ... other parameters
)
```

**Performance-optimized** (keep containers warm longer):

```python
@app.cls(
    scaledown_window=1800,  # 30 minutes
    # ... other parameters
)
```

**Current setting** (cost-optimized for testing):

```python
@app.cls(
    scaledown_window=10,  # 10 seconds (very aggressive for cost savings)
    # ... other parameters
)
```

## Additional Scaling Parameters

Modal also supports other scaling parameters:

- **`min_containers`**: Minimum number of containers to keep running
- **`max_containers`**: Maximum number of containers to scale up to
- **`buffer_containers`**: Number of extra containers to keep ready
- **`keep_warm`**: Number of containers to keep warm (always running)

## Dynamic Updates

You can update scaling settings without redeploying using the Modal API:

```python
import modal

app = modal.App.lookup("ollama-service")
service = app.OllamaService()

# Update scaledown_window dynamically
service.update_autoscaler(scaledown_window=300)
```

## References

- [Modal Scaling Documentation](https://modal.com/docs/guide/scale)
- [Modal API Reference - @app.cls](https://modal.com/docs/reference/modal.App#modal.App.cls)
