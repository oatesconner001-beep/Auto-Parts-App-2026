"""
Gemini Vision image comparison for auto parts.

Uses google-genai (already installed) with gemini-1.5-flash model which supports
inline image data and has a much higher free quota than the preview model:
  - Free tier: 1,500 requests/day, 15 requests/minute
  - Completely free — no billing required

Usage:
    from src.gemini_vision import compare_images, is_available

    result = compare_images(url1, url2, part_type="ENGINE MOUNT")
    # Returns: {"match": "YES"|"LIKELY"|"UNCERTAIN"|"NO",
    #           "confidence": 0-100, "reasoning": "...", "error": None}
"""

import os
import re
import json
import time
import base64
from pathlib import Path
import requests

# Load .env from project root
_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    for _line in _env_path.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

# gemini-3-flash-preview: works with this API key, supports vision (multimodal)
# Same model as gemini_compare.py — free tier, auto-disables on 429 quota error
GEMINI_VISION_MODEL = "gemini-3-flash-preview"

_client = None
_quota_exhausted = False
_last_request_time = 0.0
_MIN_INTERVAL = 4.1  # seconds between requests to stay under 15 RPM


def is_available() -> bool:
    """Returns False once daily quota has been hit this session."""
    return not _quota_exhausted


def _get_client():
    global _client
    if _client is None:
        from google import genai
        api_key = os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY not set in .env")
        _client = genai.Client(api_key=api_key)
    return _client


def _download_image_b64(url: str) -> tuple[str, str]:
    """
    Download an image from a URL and return (base64_string, mime_type).
    Raises on failure.
    """
    resp = requests.get(url, timeout=15, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
    })
    resp.raise_for_status()
    content_type = resp.headers.get("Content-Type", "image/jpeg").split(";")[0].strip()
    if content_type not in ("image/jpeg", "image/png", "image/webp", "image/gif"):
        content_type = "image/jpeg"
    b64 = base64.b64encode(resp.content).decode("utf-8")
    return b64, content_type


def compare_images(url1: str, url2: str, part_type: str = "",
                   brand1: str = "supplier", brand2: str = "SKP") -> dict:
    """
    Compare two part images using Gemini Vision.

    Args:
        url1:      Image URL for the supplier (brand) part
        url2:      Image URL for the SKP part
        part_type: Part type string for context (e.g. "ENGINE MOUNT")
        brand1:    Brand name for image 1 label
        brand2:    Brand name for image 2 label

    Returns:
        {
            "match":      "YES" | "LIKELY" | "UNCERTAIN" | "NO",
            "confidence": int 0-100,
            "reasoning":  str,
            "error":      str | None,
        }
    """
    global _quota_exhausted, _last_request_time

    default = {
        "match": "UNCERTAIN",
        "confidence": 0,
        "reasoning": "Gemini Vision not called.",
        "error": None,
    }

    if _quota_exhausted:
        default["reasoning"] = "Gemini Vision daily quota exhausted."
        default["error"] = "quota_exhausted"
        return default

    try:
        # Rate-limit: stay under 15 RPM
        elapsed = time.time() - _last_request_time
        if elapsed < _MIN_INTERVAL:
            time.sleep(_MIN_INTERVAL - elapsed)

        client = _get_client()

        print(f"[GeminiVision] Downloading images...")
        b64_1, mime1 = _download_image_b64(url1)
        b64_2, mime2 = _download_image_b64(url2)

        context = f"Part type: {part_type}" if part_type else ""
        prompt = f"""You are an automotive parts expert comparing two part photos to determine if they are the same part or interchangeable substitutes.

{context}
Image 1 = {brand1} part.
Image 2 = {brand2} part (potential replacement/substitute).

Instructions:
- Look at the physical shape, design, mounting points, and overall construction.
- "YES" = clearly the same part or direct substitute (identical design).
- "LIKELY" = same type of part, very similar design, minor cosmetic differences only.
- "UNCERTAIN" = similar category but unclear if interchangeable from photos alone.
- "NO" = clearly different parts (different shape, design, or mounting configuration).
- Photo quality or background differences should NOT affect your verdict.
- If one or both images are not a product photo (e.g. no-image placeholder), return UNCERTAIN.

Respond ONLY with valid JSON, no markdown:
{{"match": "YES"|"LIKELY"|"UNCERTAIN"|"NO", "confidence": <integer 0-100>, "reasoning": "<1-2 sentences>"}}"""

        from google.genai import types as gtypes

        _last_request_time = time.time()
        response = client.models.generate_content(
            model=GEMINI_VISION_MODEL,
            contents=[gtypes.Content(role="user", parts=[
                gtypes.Part.from_bytes(data=base64.b64decode(b64_1), mime_type=mime1),
                gtypes.Part.from_bytes(data=base64.b64decode(b64_2), mime_type=mime2),
                gtypes.Part.from_text(text=prompt),
            ])],
        )

        raw = response.text.strip()
        # Strip markdown fences if present
        if raw.startswith("```"):
            raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
            raw = re.sub(r"\n?```$", "", raw)
            raw = raw.strip()

        parsed = json.loads(raw)
        match = str(parsed.get("match", "UNCERTAIN")).upper()
        if match not in ("YES", "LIKELY", "UNCERTAIN", "NO"):
            match = "UNCERTAIN"
        confidence = max(0, min(100, int(parsed.get("confidence", 0))))
        reasoning = str(parsed.get("reasoning", ""))[:400]

        print(f"[GeminiVision] Result: {match} ({confidence}%)")
        return {
            "match": match,
            "confidence": confidence,
            "reasoning": reasoning,
            "error": None,
        }

    except json.JSONDecodeError as e:
        print(f"[GeminiVision] JSON parse error: {e}")
        default["error"] = f"JSON parse error: {e}"
        return default

    except Exception as e:
        err_str = str(e)
        if "429" in err_str and ("PerDay" in err_str or "quota" in err_str.lower()):
            _quota_exhausted = True
            print("[GeminiVision] Daily quota exhausted — vision comparison disabled for this session.")
            default["error"] = "quota_exhausted"
            default["reasoning"] = "Gemini Vision daily quota exhausted."
        else:
            print(f"[GeminiVision] Error: {e}")
            default["error"] = str(e)
        return default


if __name__ == "__main__":
    # Quick test
    url1 = "https://www.rockauto.com/info/28/3217-000__ra_m.jpg"
    url2 = "https://www.rockauto.com/info/983/SKM3217_1___ra_m.jpg"
    result = compare_images(url1, url2, part_type="ENGINE MOUNT",
                            brand1="ANCHOR", brand2="SKP")
    print(json.dumps(result, indent=2))
