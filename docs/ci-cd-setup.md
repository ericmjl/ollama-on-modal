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

The CI/CD pipeline deploys to a separate test environment:

- **Test App Name**: `ollama-service-test`
- **Production App Name**: `ollama-service` (unchanged)

This separation allows:

- Independent scaling and configuration
- Testing without affecting production
- Cost management (test environment can scale down quickly)

## Model Availability

The test models must be available in the test environment. Options:

### Option 1: Pre-pull Models (Recommended)

Manually pull models to the test volume before running tests:

```bash
# Deploy test environment first
modal deploy endpoint.py --name ollama-service-test

# Pull test models
modal run endpoint.py::OllamaService.pull_model \
  --model-name deepseek-r1:32b --app-name ollama-service-test
modal run endpoint.py::OllamaService.pull_model \
  --model-name llama3.2 --app-name ollama-service-test
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

- Sets up Python environment
- Installs dependencies via pixi
- Authenticates with Modal
- Deploys to test environment
- Extracts endpoint URL
- Waits for endpoint to be ready

### 2. Test Job

- Sets up Python environment
- Installs llamabot using uv
- Runs `scripts/test_gpu_routing.py` using `uv run`
- Tests H100 model routing
- Tests A10G model routing

## Troubleshooting

### Deployment Fails

- Check that `MODAL_TOKEN_ID` and `MODAL_TOKEN_SECRET` are set correctly
- Verify Modal credentials are valid
- Check workflow logs for specific error messages

### Endpoint URL Not Found

- The workflow tries multiple methods to extract the endpoint URL
- Check workflow logs to see which method succeeded
- If all methods fail, verify the app name matches `ollama-service-test`

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
export MODAL_ENDPOINT_URL="https://your-username--ollama-service-test-ollamaservice-server.modal.run"
export H100_TEST_MODEL="deepseek-r1:32b"
export A10G_TEST_MODEL="llama3.2"

uv run python scripts/test_gpu_routing.py
```

## Next Steps

1. Add GitHub secrets (`MODAL_TOKEN_ID`, `MODAL_TOKEN_SECRET`)
2. (Optional) Configure test model variables
3. Ensure test models are available in test environment
4. Push or create a PR to trigger the workflow
5. Monitor workflow execution in GitHub Actions
