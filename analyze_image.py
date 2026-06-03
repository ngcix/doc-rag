import requests
import json
import os
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from src.cli_output import configure_cli_output

    configure_cli_output()
except Exception:
    pass

GAUSS_CLIENT_KEY = os.environ.get("GAUSS_CLIENT_KEY")
GAUSS_TOKEN = os.environ.get("GAUSS_TOKEN")
GAUSS_ENDPOINT_URL = os.environ.get("GAUSS_ENDPOINT_URL")
GAUSS_USER_EMAIL = os.environ.get("GAUSS_USER_EMAIL")
YOUR_TEXT_MODEL_ID = "0198f11e-ceab-71c3-8fb1-d077d6331843"  # GaussO Flash
YOUR_I2T_MODEL_ID = "019a37fd-0c64-72c5-bb17-3b590f80be57"  #  GaussO MM - I2T(Image To Text)


def get_gauss_headers():
    """Get headers for Gauss API requests."""
    return {
        "x-generative-ai-client": GAUSS_CLIENT_KEY,
        "x-openapi-token": GAUSS_TOKEN,
        "x-generative-ai-user-email": GAUSS_USER_EMAIL,
    }


def get_llm_config():
    """Get LLM configuration."""
    return json.dumps(
        {
            "max_new_tokens": 2024,
            "seed": None,
            "top_k": 14,
            "top_p": 0.94,
            "temperature": 0.4,
            "repetition_penalty": 1.04,
        }
    )


def analyze_image_with_ai(image_path: Path, prompt: str = "Describe this image") -> dict:
    """
    Analyze an image using Gauss AI model.

    Args:
        image_path: Path to the image file
        prompt: Prompt to send to the AI model

    Returns:
        JSON response from the AI model
    """
    if not GAUSS_CLIENT_KEY or not GAUSS_TOKEN or not GAUSS_ENDPOINT_URL or not GAUSS_USER_EMAIL:
        raise ValueError("Missing Gauss API credentials. Please set the required environment variables.")

    headers = get_gauss_headers()
    llm_config = get_llm_config()

    form_data = {
        "modelIds": [YOUR_TEXT_MODEL_ID, YOUR_I2T_MODEL_ID],
        "contents": [f"{prompt}: {image_path.name}"],
        "llmConfig": llm_config,
        "isStream": False,
    }

    api_endpoint_url = f"{GAUSS_ENDPOINT_URL}/openapi/chat/v1/messages-with-models"

    try:
        with image_path.open("rb") as f:
            response = requests.post(api_endpoint_url, headers=headers, data=form_data, files=[("files", f)])
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error analyzing image: {e}")
        return {"error": str(e)}






def main():
    """Main function to demonstrate usage."""
    import argparse

    parser = argparse.ArgumentParser(description="Analyze an image using AI")
    parser.add_argument("image_path", help="Path to the image file to analyze")
    parser.add_argument("--prompt", default="Describe this image in detail", help="Prompt for AI analysis")

    args = parser.parse_args()

    # Convert string path to Path object
    image_path = Path(args.image_path)
    
    # Check if image file exists
    if not image_path.exists():
        print(f"Error: Image file not found at {image_path}")
        return

    print(f"Analyzing image: {image_path}")
    result = analyze_image_with_ai(image_path, args.prompt)
    
    print("\nAI Analysis:")
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
