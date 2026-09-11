"""Optional Gauss image-analysis client."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

TEXT_MODEL_ID = "0198f11e-ceab-71c3-8fb1-d077d6331843"
IMAGE_MODEL_ID = "019a37fd-0c64-72c5-bb17-3b590f80be57"


def _credentials() -> tuple[str, str, str, str]:
    values = (
        os.getenv("GAUSS_CLIENT_KEY", ""),
        os.getenv("GAUSS_TOKEN", ""),
        os.getenv("GAUSS_ENDPOINT_URL", ""),
        os.getenv("GAUSS_USER_EMAIL", ""),
    )
    if not all(values):
        raise ValueError("Missing required Gauss API environment variables")
    return values


def analyze_image(image_path: Path, prompt: str, session=None) -> dict[str, Any]:
    try:
        import requests
    except ImportError as exc:
        raise ImportError("Install SpecRAG with the 'image-analysis' extra") from exc

    client_key, token, endpoint, email = _credentials()
    headers = {
        "x-generative-ai-client": client_key,
        "x-openapi-token": token,
        "x-generative-ai-user-email": email,
    }
    form_data = {
        "modelIds": [TEXT_MODEL_ID, IMAGE_MODEL_ID],
        "contents": [f"{prompt}: {image_path.name}"],
        "llmConfig": json.dumps(
            {
                "max_new_tokens": 2024,
                "top_k": 14,
                "top_p": 0.94,
                "temperature": 0.4,
                "repetition_penalty": 1.04,
            }
        ),
        "isStream": False,
    }
    request = session.post if session else requests.post
    with image_path.open("rb") as image:
        response = request(
            f"{endpoint}/openapi/chat/v1/messages-with-models",
            headers=headers,
            data=form_data,
            files=[
                (
                    "files",
                    (image_path.name.replace(".pdf_", "_"), image, "image/png"),
                )
            ],
            timeout=120,
        )
    response.raise_for_status()
    return response.json()


def extract_content(response: dict[str, Any]) -> str:
    if not isinstance(response, dict) or "error" in response:
        return ""
    actions = response.get("actions") or []
    if actions:
        action = actions[0]
        for key in ("response", "answer", "content"):
            if key in action:
                return str(action[key])
    if "content" in response:
        return str(response["content"])
    choices = response.get("choices") or []
    if choices:
        choice = choices[0]
        if "message" in choice:
            return str(choice["message"].get("content", ""))
        return str(choice.get("content", ""))
    return str(response.get("result", ""))
