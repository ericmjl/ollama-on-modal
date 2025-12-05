# Why endpoint.py is the Right Choice

This document explains why `endpoint.py` is the correct file to use for deployment, based on our investigation and fixes.

## Investigation Summary

We investigated the git history and found:

1. **Original `endpoint.py`** was deleted in May 2025 - it was a FastAPI chat completions endpoint
2. **`router.py`** exists but was never the intended deployment target
3. **Current `endpoint.py`** is the correct, working implementation

## Why endpoint.py is Correct

### 1. Matches pixi.toml Configuration

The `pixi.toml` file explicitly references `endpoint.py`:

```toml
[tasks]
deploy = "modal deploy endpoint.py"
```

This is the source of truth for what gets deployed.

### 2. Successfully Deploys

After fixing the issues documented in `fixing-deployment-issues.md`, `endpoint.py` deploys successfully to Modal without errors.

### 3. Appropriate Architecture

`endpoint.py` uses the correct Modal patterns:

- ✅ `@modal.web_server(11434)` - Directly exposes Ollama's native API
- ✅ Volume mounting for persistent model storage
- ✅ Proper GPU configuration (`gpu="H100"`)
- ✅ Service initialization in `@modal.enter()`

### 4. Simpler and More Direct

Unlike `router.py` which adds a FastAPI proxy layer, `endpoint.py`:

- Directly exposes Ollama's API without an extra proxy layer
- Reduces latency by eliminating the proxy hop
- Simpler architecture = easier to maintain

## Comparison with router.py

| Aspect | endpoint.py | router.py |
|--------|-------------|-----------|
| **Deployment target** | ✅ Yes (in pixi.toml) | ❌ No |
| **Architecture** | Direct Ollama API | FastAPI proxy |
| **Complexity** | Simpler | More complex |
| **Latency** | Lower (direct) | Higher (proxy) |
| **Status** | ✅ Active | ❌ Deprecated |

## Conclusion

**Use `endpoint.py`** - it's:
- The file referenced in `pixi.toml`
- Successfully tested and deployed
- The simpler, more direct approach
- The correct choice for this project

