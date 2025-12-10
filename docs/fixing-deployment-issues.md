# Fixing Deployment Issues

This document describes the issues encountered during deployment and how they were resolved.

## Issues Found and Fixed

### 1. Invalid `scaledown_window` Parameter (Version Issue)

**Problem**: The `@app.cls()` decorator was using `scaledown_window=10`, but Modal version 0.67.18 didn't support this parameter (or had a bug).

**Error**:

```python
TypeError: _App.cls() got an unexpected keyword argument 'scaledown_window'
```

**Solution**:

- Initially removed the parameter to get deployment working
- After updating Modal to 1.2.4+, `scaledown_window` is now supported
- Re-added with a value of 10 seconds for aggressive cost optimization (containers scale down very quickly)

**Note**: `scaledown_window` is a valid parameter in Modal 1.2.4+. The issue was due to the outdated Modal version (0.67.18).

**Fixed in**: `endpoint.py` line 50-55 (now includes `scaledown_window=10`)

### 2. Outdated Modal Client Version

**Problem**: The Modal client version (0.67.18) was too old and incompatible with the current Modal API.

**Error**:

```bash
The client version (0.67.18) is too old. Please update (pip install --upgrade modal).
```

**Solution**:

- Updated `pixi.toml` to allow newer Modal versions: changed from `modal = ">=0.67.18, <0.68"` to `modal = ">=0.67.18"`
- Ran `pixi update modal` to update to version 1.2.4

### 3. Deprecated GPU Parameter Format

**Problem**: Using `gpu=modal.gpu.H100()` format is deprecated in newer Modal versions.

**Warning**:

```python
`gpu=H100(...)` is deprecated. Use `gpu="H100"` instead.
```

**Solution**: Changed from `gpu=modal.gpu.H100()` to `gpu="H100"` (string format).

**Fixed in**: `endpoint.py` line 52

## Summary of Changes

1. **Updated Modal version**: From 0.67.18 to 1.2.4+
2. **Fixed GPU format**: Changed to string format `gpu="H100"`
3. **Re-added scaledown_window**: Now set to 10 seconds for cost optimization

## Current Working Configuration

The `endpoint.py` file now uses:

```python
@app.cls(
    volumes={"/usr/share/ollama/.ollama/models": volume},
    gpu="H100",
    scaledown_window=10,  # Scale down after 10 seconds of inactivity
    timeout=3600,  # 1 hour timeout for large model downloads
)
class OllamaService:
    # ... implementation
```

This configuration is compatible with Modal 1.2.4+ and deploys successfully.
