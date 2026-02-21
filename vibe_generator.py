"""Generate a short trip-vibe description from upvoted/downvoted images using OpenAI."""

import os
import base64
from pathlib import Path

from openai import OpenAI


def _encode_image(path: str) -> tuple[str, str]:
    """Return (base64_data, media_type) for a local image file."""
    ext = Path(path).suffix.lower()
    mime = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
    }.get(ext, "image/jpeg")

    with open(path, "rb") as f:
        data = base64.standard_b64encode(f.read()).decode("utf-8")
    return data, mime


def generate_vibe(upvoted: list[str], downvoted: list[str]) -> str:
    """Return a short vibe string derived from the upvoted images.

    Args:
        upvoted:  Paths to images the user liked.
        downvoted: Paths to images the user disliked (used to steer away from those themes).

    Returns:
        A one-sentence evocative description of the trip vibe.
    """
    if not upvoted:
        return "No vibe detected – no upvoted images provided."

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    content: list[dict] = []

    content.append({
        "type": "text",
        "text": "The following images represent the vibe the traveller WANTS:",
    })
    for path in upvoted:
        data, mime = _encode_image(path)
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:{mime};base64,{data}", "detail": "low"},
        })

    if downvoted:
        content.append({
            "type": "text",
            "text": "The following images represent vibes the traveller does NOT want:",
        })
        for path in downvoted:
            data, mime = _encode_image(path)
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:{mime};base64,{data}", "detail": "low"},
            })

    content.append({
        "type": "text",
        "text": (
            "Based on the images above, write a single short sentence (max 20 words) "
            "that captures the travel vibe the user is going for. "
            "Focus only on the upvoted images and avoid any themes present in the downvoted ones. "
            "Be evocative and specific – e.g. 'sun-drenched coastal towns with vibrant street markets "
            "and relaxed beachside cafés'. "
            "Return only the vibe description, nothing else."
        ),
    })

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": content}],
        max_tokens=80,
    )

    return response.choices[0].message.content.strip()
