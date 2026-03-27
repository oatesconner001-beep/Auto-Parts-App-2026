"""
Local vision comparison for auto parts — free, unlimited, runs on your GPU.

Uses Ollama (https://ollama.com) with a local vision model — no API key, no quota,
no internet required after initial model download.

Recommended models (choose one based on quality vs speed preference):
  llava-phi3   — Microsoft Phi-3 Vision, 4.1 GB VRAM, BEST quality/speed ratio
  llava:7b     — LLaVA 7B, ~5 GB VRAM, strong reasoning
  moondream    — 1.8 GB, fastest, slightly lower quality

SETUP (one-time, ~5 minutes):
  1. Download Ollama for Windows: https://ollama.com/download/windows
     (or: winget install Ollama.Ollama)
  2. After install, open a terminal and run:
         ollama pull llava-phi3
  3. Ollama runs as a background service on http://localhost:11434

USAGE:
    from src.local_vision import compare_images, is_available, check_ollama

    ok, msg = check_ollama()      # verify Ollama is running + model is loaded
    print(ok, msg)

    result = compare_images(url1, url2, part_type="ENGINE MOUNT",
                            brand1="ANCHOR", brand2="SKP")
    # Returns: {"match": "YES"|"LIKELY"|"UNCERTAIN"|"NO",
    #           "confidence": 0-100, "reasoning": "...", "error": None}

This module is a drop-in replacement for gemini_vision.py — same function signature,
same return format. Switch by changing the import in run_image_analysis.py.
"""

import re
import json
import base64
import time
import requests
from typing import Optional
from PIL import Image

# ─── Configuration ────────────────────────────────────────────────────────────

OLLAMA_URL   = "http://localhost:11434"
# Preferred model order — first available one is used.
# moondream: 1.8 GB, fast, reliable with current Ollama  (preferred)
# llava-phi3: 2.9 GB — known llama-sampling.cpp assertion crash on Ollama v0.18.0
# llava:7b:   5 GB  — reliable but large
PREFERRED_MODELS = ["moondream", "llava-phi3", "llava:7b"]
DEFAULT_MODEL = "moondream"

_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"}


# ─── Availability check ───────────────────────────────────────────────────────

def is_available(model: str = DEFAULT_MODEL) -> bool:
    """Returns True if Ollama is running and the vision model is available."""
    ok, _ = check_ollama(model)
    return ok


def check_ollama(model: str = DEFAULT_MODEL) -> tuple[bool, str]:
    """
    Verify Ollama is running and the requested model is pulled.
    If model is DEFAULT_MODEL, auto-selects the best available from PREFERRED_MODELS.
    Returns (True, "OK") or (False, "reason string").
    """
    global DEFAULT_MODEL
    try:
        resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        resp.raise_for_status()
        available = [m["name"].split(":")[0] for m in resp.json().get("models", [])]

        # Auto-select best available model from preferred list
        if model == DEFAULT_MODEL or model in PREFERRED_MODELS:
            for preferred in PREFERRED_MODELS:
                if preferred.split(":")[0] in available:
                    if preferred != DEFAULT_MODEL:
                        print(f"[LocalVision] Auto-selected model: {preferred}")
                        DEFAULT_MODEL = preferred
                    return True, "OK"

        model_base = model.split(":")[0]
        if model_base not in available:
            return False, (
                f"Model '{model}' not found. Pull it first:\n"
                f"  ollama pull {model}\n"
                f"Available models: {', '.join(available) or '(none)'}"
            )
        return True, "OK"
    except requests.exceptions.ConnectionError:
        return False, (
            "Ollama is not running. Start it:\n"
            "  1. Install from https://ollama.com/download/windows\n"
            "  2. It starts automatically as a background service\n"
            "  3. Or run: ollama serve"
        )
    except Exception as e:
        return False, f"Ollama check failed: {e}"


# ─── Image helpers ────────────────────────────────────────────────────────────

# Each panel max size in the composite. The composite will be ~512 x 256 total.
MAX_PANEL_PX = 256


def _download_image(url: str):
    """Download an image URL and return a PIL Image (RGB)."""
    from PIL import Image
    from io import BytesIO
    resp = requests.get(url, timeout=15, headers=_HEADERS)
    resp.raise_for_status()
    return Image.open(BytesIO(resp.content)).convert("RGB")


def _make_composite(img1, img2, max_px: int = MAX_PANEL_PX) -> str:
    """
    Create a side-by-side composite of two PIL images and return as base64 JPEG.

    Sending TWO separate images to llava-phi3 via Ollama causes 500 errors
    (model limitation — only one image per request is stable).  Compositing
    both panels into a single image works around this completely.
    """
    from PIL import Image, ImageDraw, ImageFont
    from io import BytesIO

    def fit(img, size):
        img = img.copy()
        img.thumbnail((size, size), Image.LANCZOS)
        return img

    p1 = fit(img1, max_px)
    p2 = fit(img2, max_px)
    gap = 4
    w = p1.width + gap + p2.width
    h = max(p1.height, p2.height)
    canvas = Image.new("RGB", (w, h), (200, 200, 200))
    canvas.paste(p1, (0, (h - p1.height) // 2))
    canvas.paste(p2, (p1.width + gap, (h - p2.height) // 2))

    buf = BytesIO()
    canvas.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


# ─── Main comparison function ─────────────────────────────────────────────────

def compare_images(url1: str, url2: str, part_type: str = "",
                   brand1: str = "supplier", brand2: str = "SKP",
                   model: str = DEFAULT_MODEL) -> dict:
    """
    Compare two part images using a local Ollama vision model.

    Drop-in replacement for gemini_vision.compare_images() — identical signature
    and return format.

    Args:
        url1:      Product image URL for the supplier (brand) part
        url2:      Product image URL for the SKP replacement part
        part_type: Part type for context, e.g. "ENGINE MOUNT"
        brand1:    Label for image 1 in the prompt
        brand2:    Label for image 2 in the prompt
        model:     Ollama model to use (default: llava-phi3)

    Returns:
        {
            "match":      "YES" | "LIKELY" | "UNCERTAIN" | "NO",
            "confidence": int 0-100,
            "reasoning":  str,
            "error":      str | None,
        }
    """
    default = {
        "match": "UNCERTAIN",
        "confidence": 0,
        "reasoning": "Local vision not called.",
        "error": None,
    }

    # Quick availability check
    ok, msg = check_ollama(model)
    if not ok:
        default["error"] = msg
        default["reasoning"] = f"Ollama unavailable: {msg}"
        print(f"[LocalVision] {msg}")
        return default

    try:
        print(f"[LocalVision] Downloading images...")
        t0 = time.time()
        pil1 = _download_image(url1)
        pil2 = _download_image(url2)
        print(f"[LocalVision] Images downloaded in {time.time()-t0:.1f}s")

        # Composite both images side-by-side into ONE image.
        # llava-phi3 has a known issue with multiple entries in the images[] array
        # (returns 500). A composite panel is a reliable workaround.
        composite_b64 = _make_composite(pil1, pil2)
        print(f"[LocalVision] Composite image created ({len(composite_b64)//1024} KB b64)")

        print(f"[LocalVision] Running {model} (describe-and-compare)...")
        t1 = time.time()

        def _describe(b64: str, label: str) -> str:
            """Ask the model to describe a single part image."""
            prompt_d = (
                f"This is a product photo of an auto part{(' (' + part_type + ')') if part_type else ''}. "
                f"Describe its physical shape, main material, and any visible mounting or attachment features "
                f"in one or two short sentences."
            )
            for endpoint, payload in [
                ("/api/chat",     {"model": model, "stream": False, "options": {"temperature": 0.1, "num_predict": 80},
                                   "messages": [{"role": "user", "content": prompt_d, "images": [b64]}]}),
                ("/api/generate", {"model": model, "stream": False, "options": {"temperature": 0.1, "num_predict": 80},
                                   "prompt": prompt_d, "images": [b64]}),
            ]:
                r = requests.post(f"{OLLAMA_URL}{endpoint}", json=payload, timeout=60)
                if r.status_code == 200:
                    if "chat" in endpoint:
                        return r.json().get("message", {}).get("content", "").strip()
                    return r.json().get("response", "").strip()
            return ""

        # Encode each image individually (full panel, not composite) for better quality
        def _img_to_b64(pil_img) -> str:
            from io import BytesIO as _BIO
            tmp = pil_img.copy()
            tmp.thumbnail((400, 400), Image.LANCZOS)
            buf = _BIO()
            tmp.save(buf, format="JPEG", quality=85)
            return base64.b64encode(buf.getvalue()).decode()

        b64_a = _img_to_b64(pil1)
        b64_b = _img_to_b64(pil2)

        desc1 = _describe(b64_a, brand1)
        desc2 = _describe(b64_b, brand2)
        elapsed = time.time() - t1
        print(f"[LocalVision] Descriptions in {elapsed:.1f}s")
        print(f"[LocalVision]   {brand1}: {desc1[:80]}")
        print(f"[LocalVision]   {brand2}: {desc2[:80]}")

        if not desc1 or not desc2:
            default["error"] = "Empty description from model"
            return default

        # Text similarity: Jaccard on meaningful words (3+ chars, not stop words)
        _stop = {"the", "and", "for", "with", "this", "that", "its", "has", "are",
                  "from", "can", "which", "two", "one", "any", "all"}
        def _words(s):
            return {w for w in re.findall(r'\b[a-z]{3,}\b', s.lower()) if w not in _stop}

        w1, w2 = _words(desc1), _words(desc2)
        shared = w1 & w2
        union = w1 | w2
        jaccard = len(shared) / len(union) if union else 0.0
        print(f"[LocalVision] Jaccard similarity: {jaccard:.2f}  shared={shared}")

        # Map Jaccard to verdict
        if jaccard >= 0.45:
            match = "YES"; confidence = 85
        elif jaccard >= 0.25:
            match = "LIKELY"; confidence = 70
        elif jaccard >= 0.10:
            match = "UNCERTAIN"; confidence = 40
        else:
            match = "NO"; confidence = 20

        reasoning = f"Image descriptions: [{brand1}] {desc1[:150]} | [{brand2}] {desc2[:150]}"

        print(f"[LocalVision] Result: {match} ({confidence}%)  jaccard={jaccard:.2f}")
        return {
            "match":      match,
            "confidence": confidence,
            "reasoning":  reasoning[:400],
            "error":      None,
        }

    except json.JSONDecodeError as e:
        msg = f"JSON parse error: {e}"
        print(f"[LocalVision] {msg}")
        default["error"] = msg
        return default

    except requests.exceptions.Timeout:
        msg = "Inference timed out (>120s). Try a smaller model or restart Ollama."
        print(f"[LocalVision] {msg}")
        default["error"] = msg
        return default

    except Exception as e:
        print(f"[LocalVision] Error: {e}")
        default["error"] = str(e)
        return default


# ─── CLI test ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    print("=" * 60)
    print("Local Vision Test — Ollama")
    print("=" * 60)

    # Check Ollama is up
    ok, msg = check_ollama()
    if not ok:
        print(f"\nERROR: {msg}")
        sys.exit(1)
    print(f"Ollama: OK  (model: {DEFAULT_MODEL})\n")

    # Test with known motor mount pair
    url1 = "https://www.rockauto.com/info/28/3217-000__ra_m.jpg"
    url2 = "https://www.rockauto.com/info/983/SKM3217_1___ra_m.jpg"

    print(f"Comparing ANCHOR 3217 vs SKP SKM3217 (ENGINE MOUNT)")
    print(f"URL1: {url1}")
    print(f"URL2: {url2}")
    print()

    result = compare_images(url1, url2, part_type="ENGINE MOUNT",
                            brand1="ANCHOR", brand2="SKP")
    print("\nResult:")
    print(json.dumps(result, indent=2))
