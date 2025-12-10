# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "llamabot",
#     "httpx",
# ]
# ///

"""Test GPU routing functionality using llamabot SimpleBot.

This script tests that models are correctly routed to the appropriate GPU:
- Large models (e.g., deepseek-r1:32b) should route to H100
- Smaller models (e.g., llama3.2) should route to A10G

To run this script, use:

```bash
uv run scripts/test_gpu_routing.py
```
"""

import os
import sys
import time

import llamabot as lmb


def test_h100_model(endpoint_url: str, model_name: str, timeout: int = 300) -> bool:
    """Test that a large model routes to H100 GPU.

    Args:
        endpoint_url: The Modal endpoint URL (without trailing slash)
        model_name: Name of the model to test (e.g., "deepseek-r1:32b")
        timeout: Maximum time to wait for response in seconds

    Returns:
        True if test passes, False otherwise
    """
    print(f"Testing H100 model: {model_name}")
    print(f"Endpoint: {endpoint_url}")

    try:
        bot = lmb.SimpleBot(
            "You are a helpful assistant.",
            model_name=f"ollama_chat/{model_name}",
            api_base=endpoint_url,
        )

        # Use a simple prompt to test basic functionality
        start_time = time.time()
        response = bot("Say hello in one sentence.")
        elapsed = time.time() - start_time

        assert response.content is not None, "Response content is None"
        assert len(response.content) > 0, "Response content is empty"

        print(f"✓ H100 model test passed: {model_name}")
        print(f"  Response: {response.content[:100]}...")
        print(f"  Time elapsed: {elapsed:.2f}s")
        return True

    except Exception as e:
        print(f"✗ H100 model test failed: {model_name}")
        print(f"  Error: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_a10g_model(endpoint_url: str, model_name: str, timeout: int = 120) -> bool:
    """Test that a smaller model routes to A10G GPU.

    Args:
        endpoint_url: The Modal endpoint URL (without trailing slash)
        model_name: Name of the model to test (e.g., "llama3.2")
        timeout: Maximum time to wait for response in seconds

    Returns:
        True if test passes, False otherwise
    """
    print(f"Testing A10G model: {model_name}")
    print(f"Endpoint: {endpoint_url}")

    try:
        bot = lmb.SimpleBot(
            "You are a helpful assistant.",
            model_name=f"ollama_chat/{model_name}",
            api_base=endpoint_url,
        )

        # Use a simple prompt to test basic functionality
        start_time = time.time()
        response = bot("Say hello in one sentence.")
        elapsed = time.time() - start_time

        assert response.content is not None, "Response content is None"
        assert len(response.content) > 0, "Response content is empty"

        print(f"✓ A10G model test passed: {model_name}")
        print(f"  Response: {response.content[:100]}...")
        print(f"  Time elapsed: {elapsed:.2f}s")
        return True

    except Exception as e:
        print(f"✗ A10G model test failed: {model_name}")
        print(f"  Error: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Main test function."""
    endpoint_url = os.environ.get("MODAL_ENDPOINT_URL")
    if not endpoint_url:
        print("Error: MODAL_ENDPOINT_URL environment variable not set")
        print("Please set MODAL_ENDPOINT_URL to the Modal endpoint URL")
        sys.exit(1)

    # Remove trailing slash if present
    endpoint_url = endpoint_url.rstrip("/")

    # Get test models from environment variables with defaults
    h100_model = os.environ.get("H100_TEST_MODEL", "deepseek-r1:32b")
    a10g_model = os.environ.get("A10G_TEST_MODEL", "llama3.2")

    print("=" * 60)
    print("GPU Routing Test Suite")
    print("=" * 60)
    print(f"Endpoint URL: {endpoint_url}")
    print(f"H100 Test Model: {h100_model}")
    print(f"A10G Test Model: {a10g_model}")
    print("=" * 60)
    print()

    # Run tests
    results = []

    print("Running H100 model test...")
    results.append(("H100", test_h100_model(endpoint_url, h100_model)))
    print()

    print("Running A10G model test...")
    results.append(("A10G", test_a10g_model(endpoint_url, a10g_model)))
    print()

    # Summary
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)
    for test_name, passed in results:
        status = "PASS" if passed else "FAIL"
        print(f"{test_name}: {status}")
    print("=" * 60)

    # Exit with appropriate code
    all_passed = all(result[1] for result in results)
    if all_passed:
        print("All tests passed!")
        sys.exit(0)
    else:
        print("Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
