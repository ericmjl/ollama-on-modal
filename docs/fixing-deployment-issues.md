# Fixing Deployment Issues

This document describes the issues encountered during deployment and how they were resolved.

## Issues Found and Fixed

### 1. Invalid `scaledown_window` Parameter (Version Issue)

**Problem**: The `@app.cls()` decorator was using `scaledown_window=10`, but Modal version 0.67.18 didn't support this parameter (or had a bug).

**Error**:

```
TypeError: _App.cls() got an unexpected keyword argument 'scaledown_window'
```

**Solution**:

- Initially removed the parameter to get deployment working
- After updating Modal to 1.2.4, `scaledown_window` is now supported
- Re-added with a reasonable value (600 seconds = 10 minutes) for cost optimization

**Note**: `scaledown_window` is a valid parameter in Modal 1.2.4+. The issue was due to the outdated Modal version (0.67.18).

**Fixed in**: `endpoint.py` line 50-53 (now includes `scaledown_window=600`)

### 2. Outdated Modal Client Version

**Problem**: The Modal client version (0.67.18) was too old and incompatible with the current Modal API.

**Error**:

```
The client version (0.67.18) is too old. Please update (pip install --upgrade modal).
```

**Solution**:

- Updated `pixi.toml` to allow newer Modal versions: changed from `modal = ">=0.67.18, <0.68"` to `modal = ">=0.67.18"`
- Ran `pixi update modal` to update to version 1.2.4

### 3. Deprecated GPU Parameter Format

**Problem**: Using `gpu=modal.gpu.H100()` format is deprecated in newer Modal versions.

**Warning**:

```
`gpu=H100(...)` is deprecated. Use `gpu="H100"` instead.
```

**Solution**: Changed from `gpu=modal.gpu.H100()` to `gpu="H100"` (string format).

**Fixed in**: `endpoint.py` line 52

## Summary of Changes

1. **Removed invalid parameter**: `scaledown_window=10` from `@app.cls()` decorator
2. **Updated Modal version**: From 0.67.18 to 1.2.4
3. **Fixed GPU format**: Changed to string format `gpu="H100"`

## Current Working Configuration

The `endpoint.py` file now uses:

```python
@app.cls(
    volumes={"/usr/share/ollama/.ollama/models": volume},
    gpu="H100",
)
class OllamaService:
    # ... implementation
```

This configuration is compatible with Modal 1.2.4+ and deploys successfully.
