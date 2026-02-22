"""Generate a short trip-vibe description from upvoted/downvoted images.

Supports multiple LLM providers:
- OpenAI (default): gpt-4o-mini with vision
- Anthropic/Claude: claude-sonnet with vision (200K context)
- Falls back to OpenAI if provider not configured
"""

import os
import base64
from pathlib import Path
from urllib.parse import urlparse

import httpx


def _encode_image(source: str) -> tuple[str, str]:
    """Return (base64_data, media_type) for a local file path or a remote URL."""
    parsed = urlparse(source)
    is_url = parsed.scheme in ("http", "https")

    if is_url:
        response = httpx.get(source, timeout=10, follow_redirects=True)
        response.raise_for_status()
        raw = response.content
        content_type = response.headers.get("content-type", "image/jpeg")
        mime = content_type.split(";")[0].strip()
    else:
        ext = Path(source).suffix.lower()
        mime = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
        }.get(ext, "image/jpeg")
        with open(source, "rb") as f:
            raw = f.read()

    data = base64.standard_b64encode(raw).decode("utf-8")
    return data, mime


_VIBE_INSTRUCTION = (
    "Based on the images above, write a single short sentence (max 20 words) "
    "that captures the travel vibe the user is going for. "
    "Focus only on the upvoted images and avoid any themes present in the downvoted ones. "
    "Be evocative and specific — e.g. 'sun-drenched coastal towns with vibrant street markets "
    "and relaxed beachside cafés'. "
    "Return only the vibe description, nothing else."
)


def _generate_vibe_anthropic(upvoted: list[str], downvoted: list[str]) -> str:
    """Generate vibe using Anthropic Claude's vision API."""
    import anthropic

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    model = os.getenv("LLM_MODEL", "claude-sonnet-4-20250514")

    content: list[dict] = []

    content.append({"type": "text", "text": "The following images represent the vibe the traveller WANTS:"})
    for path in upvoted:
        data, mime = _encode_image(path)
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": mime, "data": data},
        })

    if downvoted:
        content.append({"type": "text", "text": "The following images represent vibes the traveller does NOT want:"})
        for path in downvoted:
            data, mime = _encode_image(path)
            content.append({
                "type": "image",
                "source": {"type": "base64", "media_type": mime, "data": data},
            })

    content.append({"type": "text", "text": _VIBE_INSTRUCTION})

    response = client.messages.create(
        model=model,
        max_tokens=80,
        messages=[{"role": "user", "content": content}],
    )
    return response.content[0].text.strip()


def _generate_vibe_openai(upvoted: list[str], downvoted: list[str]) -> str:
    """Generate vibe using OpenAI's vision API."""
    from openai import OpenAI

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    content: list[dict] = []
    content.append({"type": "text", "text": "The following images represent the vibe the traveller WANTS:"})
    for path in upvoted:
        data, mime = _encode_image(path)
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:{mime};base64,{data}", "detail": "low"},
        })

    if downvoted:
        content.append({"type": "text", "text": "The following images represent vibes the traveller does NOT want:"})
        for path in downvoted:
            data, mime = _encode_image(path)
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:{mime};base64,{data}", "detail": "low"},
            })

    content.append({"type": "text", "text": _VIBE_INSTRUCTION})

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": content}],
        max_tokens=80,
    )
    return response.choices[0].message.content.strip()


def generate_vibe(upvoted: list[str], downvoted: list[str]) -> str:
    """Return a short vibe string derived from the upvoted images.

    Automatically selects the LLM provider based on the LLM_PROVIDER env var.

    Args:
        upvoted:  Paths to images the user liked.
        downvoted: Paths to images the user disliked (used to steer away from those themes).

    Returns:
        A one-sentence evocative description of the trip vibe.
    """
    if not upvoted:
        return "No vibe detected – no upvoted images provided."

    provider = os.getenv("LLM_PROVIDER", "openai").lower().strip()

    if provider == "anthropic" and os.getenv("ANTHROPIC_API_KEY"):
        return _generate_vibe_anthropic(upvoted, downvoted)
    else:
        return _generate_vibe_openai(upvoted, downvoted)
