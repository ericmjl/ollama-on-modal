# CI/CD Setup Guide

This document explains how to set up the CI/CD testing harness for GPU routing.

## Overview

The CI/CD pipeline automatically:

1. Deploys to Modal test environment on push/PR
2. Waits for deployment to complete
3. Runs integration tests using llamabot SimpleBot
4. Verifies GPU routing for H100 and A10G models

## GitHub Secrets Configuration

To enable the CI/CD pipeline, you need to configure the following GitHub secrets:

### Required Secrets

1. **`MODAL_TOKEN_ID`**
   - Your Modal token ID
   - Get it from: <https://modal.com/settings/tokens>
   - Or run: `modal token current` and look for the token ID

2. **`MODAL_TOKEN_SECRET`**
   - Your Modal token secret
   - Get it from: <https://modal.com/settings/tokens>
   - Or run: `modal token current` and look for the token secret

### How to Add Secrets

1. Go to your GitHub repository
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add each secret:
   - Name: `MODAL_TOKEN_ID`
   - Value: Your Modal token ID
5. Repeat for `MODAL_TOKEN_SECRET`

### Verifying Secrets

After adding secrets, the workflow will automatically use them when triggered.
You can verify they're set correctly by checking the workflow logs
(the deploy step should authenticate successfully).

## GitHub Variables (Optional)

You can configure test models via GitHub repository variables:

1. Go to **Settings** → **Secrets and variables** → **Actions** → **Variables** tab
2. Add variables:
   - `H100_TEST_MODEL`: Model name for H100 testing (default: `deepseek-r1:32b`)
   - `A10G_TEST_MODEL`: Model name for A10G testing (default: `llama3.2`)

## Test Environment

The CI/CD pipeline deploys to a separate Modal environment:

- **Modal Environment**: `test` (separate from `main`/production)
- **App Name**: `ollama-service` (consistent across all environments)
- **Deployment Command**: `modal deploy endpoint.py --env test`
- **Endpoint URL Format**:
  `https://{username}-{env-suffix}--{app-name}-{class-name}-{method-name}.modal.run`
  - Test: `https://ericmjl-test--ollama-service-ollamaservice-server.modal.run`
  - Production: `https://ericmjl--ollama-service-ollamaservice-server.modal.run`

This separation allows:

- Independent scaling and configuration
- Testing without affecting production
- Cost management (test environment can scale down quickly)
- Separate secrets and resources per environment

## Model Availability

The test models must be available in the test environment. Options:

### Option 1: Pre-pull Models (Recommended)

Manually pull models to the test volume before running tests:

```bash
# Deploy test environment first
pixi run deploy --env test
# Or: modal deploy endpoint.py --env test

# Pull all test models at once
pixi run pull-test-models

# Or pull individual models
pixi run pull-test-model-h100  # Pulls deepseek-r1:32b
pixi run pull-test-model-a10g  # Pulls llama3.2
```

### Option 2: Pull During Test Setup

Modify the workflow to pull models as part of the deployment step
(adds time but ensures models are available).

### Option 3: Use Existing Models

If models are already in the shared volume, they'll be available automatically.

## Workflow Triggers

The workflow triggers on:

- **Push** to `main` or `develop` branches
- **Pull requests** (opened, synchronized, or reopened)

## Workflow Jobs

### 1. Deploy Job

- Sets up pixi environment
- Installs dependencies via pixi
- Authenticates with Modal using secrets
- Deploys to test environment using `--env test`
- Sets hard-coded endpoint URL (TODO: extract dynamically)
- Waits for endpoint to be ready

### 2. Test Job

- Sets up Python environment
- Installs uv
- Runs `scripts/test_gpu_routing.py` using `uv run`
  - Script uses inline metadata (PEP 723) for dependencies
  - Automatically installs `llamabot` and `httpx`
- Tests H100 model routing
- Tests A10G model routing

**Note**: Currently, all models run on H100 GPU. GPU routing based on model
name has not been implemented yet (see [issue #1](https://github.com/ericmjl/ollama-on-modal/issues/1)).

## Troubleshooting

### Deployment Fails

- Check that `MODAL_TOKEN_ID` and `MODAL_TOKEN_SECRET` are set correctly
- Verify Modal credentials are valid
- Check workflow logs for specific error messages

### Endpoint URL Not Found

- The endpoint URL is currently hard-coded in the workflow
- Test environment URL:
  `https://ericmjl-test--ollama-service-ollamaservice-server.modal.run`
- Production URL:
  `https://ericmjl--ollama-service-ollamaservice-server.modal.run`
- TODO: Extract dynamically from deployment output (see workflow comments)

### Tests Fail

- Verify test models are available in the test environment
- Check that models are pulled to the test volume
- Review test output for specific error messages
- Ensure endpoint URL is correct and accessible

### Models Not Available

- Pull models manually to the test volume (see Model Availability section)
- Or modify workflow to pull models during deployment
- Check that model names match what's configured in variables

## Manual Testing

You can run the test script manually:

```bash
# For test environment
export MODAL_ENDPOINT_URL="https://ericmjl-test--ollama-service-ollamaservice-server.modal.run"
export H100_TEST_MODEL="deepseek-r1:32b"
export A10G_TEST_MODEL="llama3.2"

uv run scripts/test_gpu_routing.py
```

**Note**: Replace `ericmjl` with your Modal username in the endpoint URL.

## Current Implementation Status

### ✅ Completed

- CI/CD workflow setup with GitHub Actions
- Test environment deployment using `--env test`
- Test script with inline dependency metadata (PEP 723)
- Hard-coded endpoint URL for test environment
- Authentication with Modal using GitHub secrets

### 🚧 TODO / Future Improvements

- **Dynamic Endpoint URL Extraction**: Currently hard-coded, should extract
  from deployment output
- **GPU Routing**: Not yet implemented - all models run on H100
  (see [issue #1](https://github.com/ericmjl/ollama-on-modal/issues/1))
- **Model Pre-pulling**: Test models should be pre-pulled to test volume

## Next Steps

1. ✅ GitHub secrets configured (`MODAL_TOKEN_ID`, `MODAL_TOKEN_SECRET`)
2. (Optional) Configure test model variables
3. Ensure test models are available in test environment
4. Push or create a PR to trigger the workflow
5. Monitor workflow execution in GitHub Actions
6. Implement GPU routing feature (see [issue #1](https://github.com/ericmjl/ollama-on-modal/issues/1))
