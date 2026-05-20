# /// script
# dependencies = ["llamabot", "httpx", "loguru"]
# ///

"""Test the Ollama-on-Modal endpoints using LlamaBot."""

import httpx
from loguru import logger
from llamabot import SimpleBot

OLLAMA_BASE_URL = "https://ericmjl--ollama-service-ollamapassthrough-server.modal.run"


def test_text_model():
    """Test a text model through the passthrough endpoint."""
    logger.info("Testing text model (llama3.2)...")

    bot = SimpleBot(
        "You are a helpful assistant. Keep responses under 50 words.",
        api_base=OLLAMA_BASE_URL,
        model="ollama/llama3.2",
    )

    response = bot("What is the capital of France?")
    logger.info(f"Response: {response.content}")
    return response


def test_image_generation():
    """Test image generation through the passthrough endpoint."""
    logger.info("Testing image generation (x/flux2-klein)...")

    payload = {
        "model": "x/flux2-klein",
        "prompt": "A serene mountain lake at sunrise with pine trees and morning mist",
        "stream": False,
    }

    with httpx.Client(timeout=300.0) as client:
        response = client.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json=payload,
        )

        if response.status_code == 200:
            result = response.json()
            if result.get("done"):
                import base64
                from pathlib import Path

                image_data = result.get("image", "")
                if image_data:
                    output_path = Path("generated_image.png")
                    output_path.write_bytes(base64.b64decode(image_data))
                    logger.success(f"Image saved to {output_path}")
                else:
                    logger.warning("No image data in response")
            else:
                logger.warning(f"Generation not complete: {result}")
        else:
            logger.error(f"Request failed: {response.status_code} - {response.text}")


if __name__ == "__main__":
    logger.info("=== Ollama-on-Modal Endpoint Tests ===")
    test_text_model()
    test_image_generation()
    logger.info("=== Done ===")
