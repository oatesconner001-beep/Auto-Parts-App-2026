"""
Local text comparison for auto parts using Mistral 7B via Ollama — completely free.

This is a drop-in replacement for gemini_compare.py that uses a local Mistral LLM
instead of the Google Gemini API. Eliminates quota limits and API dependencies.

Uses Ollama (https://ollama.com) with Mistral 7B Instruct — no API key, no quota,
no internet required after initial model download.

SETUP (one-time, ~5-10 minutes):
  1. Ollama should already be installed and running (from vision setup)
  2. Install the model: ollama pull mistral
  3. Ollama runs as a background service on http://localhost:11434

USAGE:
    from local_text_compare import compare_parts, is_available

Drop-in replacement for gemini_compare.py — identical function signature and return format.
"""

import re
import json
import time
import requests
from typing import Optional


# Configuration
OLLAMA_URL = "http://localhost:11434"
MISTRAL_MODEL = "mistral"
BACKUP_MODELS = ["mistral:latest", "llama2:7b", "llama2"]  # Fallback options

# Global state for quota/availability tracking (same pattern as gemini_compare)
_ollama_disabled = False


def is_available() -> bool:
    """
    Returns True if Ollama is running and a text model is available.
    Returns False if previously disabled due to errors (resets on new process).
    """
    return not _ollama_disabled and _check_ollama()


def _check_ollama() -> bool:
    """Quick check if Ollama is running and has a text model available."""
    try:
        resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        resp.raise_for_status()
        available = [m["name"].split(":")[0] for m in resp.json().get("models", [])]

        # Check if any of our preferred models are available
        for model in [MISTRAL_MODEL] + BACKUP_MODELS:
            if model.split(":")[0] in available:
                return True
        return False
    except:
        return False


def _get_best_model() -> Optional[str]:
    """Get the best available text model, preferring Mistral."""
    try:
        resp = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        resp.raise_for_status()
        available = [m["name"].split(":")[0] for m in resp.json().get("models", [])]

        for model in [MISTRAL_MODEL] + BACKUP_MODELS:
            base_name = model.split(":")[0]
            if base_name in available:
                return model
        return None
    except:
        return None


def _build_prompt(anchor_data: dict, skp_data: dict, part_type: str,
                  rule_confidence: int, rule_reason: str) -> str:
    """Build the comparison prompt for Mistral (same format as Gemini)."""

    def fmt(d: dict) -> str:
        lines = [
            f"  Part Number: {d.get('part_number', 'N/A')}",
            f"  Brand: {d.get('brand', 'N/A')}",
            f"  Found on RockAuto: {d.get('found', False)}",
        ]
        if d.get("category"):
            lines.append(f"  Category: {d['category']}")
        if d.get("oem_refs"):
            lines.append(f"  OEM/Interchange Numbers: {', '.join(d['oem_refs'])}")
        if d.get("price"):
            lines.append(f"  Price: {d['price']}")
        if d.get("description"):
            lines.append(f"  Description: {d['description'][:400]}")
        if d.get("features"):
            lines.append(f"  Features: {'; '.join(d['features'][:5])}")
        if d.get("specs"):
            specs_str = "; ".join(f"{k}={v}" for k, v in list(d["specs"].items())[:6])
            lines.append(f"  Specs: {specs_str}")
        if d.get("error"):
            lines.append(f"  Not found reason: {d['error']}")
        return "\n".join(lines)

    return f"""You are an automotive parts compatibility expert. The rule-based system flagged this comparison as UNCERTAIN ({rule_confidence}% confidence).

Rule-based reasoning: {rule_reason}

Please make the final determination on whether these two parts are interchangeable.

PART TYPE (from buyer's catalog): {part_type}

ANCHOR PART:
{fmt(anchor_data)}

SKP PART:
{fmt(skp_data)}

MATCHING RULES:
1. Shared OEM/interchange numbers = STRONGEST signal (same OEM # = same vehicle application)
2. Same category = necessary but not sufficient
3. Similar descriptions/features = supporting evidence
4. Price difference alone is NOT a mismatch signal
5. If a part is NOT found on RockAuto = UNCERTAIN (not NO)

Respond with ONLY a single line of valid JSON. No explanations, no markdown fences, no text before or after:

{{"match_result": "YES", "confidence": 85, "match_reason": "Brief reason here", "fitment_match": "YES", "desc_match": "YES", "missing_info": "None"}}"""


def compare_parts(anchor_data: dict, skp_data: dict, part_type: str,
                  rule_confidence: int = 0, rule_reason: str = "") -> dict:
    """
    Use local Mistral 7B to compare two parts when rules are uncertain.

    Drop-in replacement for gemini_compare.compare_parts() with identical signature and return format.

    Args:
        anchor_data:      Dict from scrape_rockauto()
        skp_data:         Dict from scrape_rockauto()
        part_type:        Part type string from col A
        rule_confidence:  Confidence % from rule_compare (for context in prompt)
        rule_reason:      Reason string from rule_compare

    Returns same dict schema as rule_compare.compare_parts()
    """
    global _ollama_disabled

    default = {
        "match_result":  "UNCERTAIN",
        "confidence":    0,
        "match_reason":  "Local text comparison failed — see missing_info.",
        "fitment_match": "UNKNOWN",
        "desc_match":    "UNKNOWN",
        "missing_info":  "",
    }

    if _ollama_disabled:
        default["missing_info"] = "Local LLM disabled due to previous errors"
        return default

    try:
        model = _get_best_model()
        if not model:
            _ollama_disabled = True
            default["missing_info"] = "No compatible text model found. Install: ollama pull mistral"
            print("[LocalText] No text model available — disabling for this session")
            return default

        prompt = _build_prompt(anchor_data, skp_data, part_type, rule_confidence, rule_reason)

        print(f"[LocalText] Comparing {anchor_data.get('part_number')} vs {skp_data.get('part_number')} using {model}...")

        start_time = time.time()

        # Try Ollama's chat endpoint first (preferred), fallback to generate endpoint
        for endpoint, payload in [
            ("/api/chat", {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "stream": False,
                "options": {"temperature": 0.1, "num_predict": 256}
            }),
            ("/api/generate", {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.1, "num_predict": 256}
            })
        ]:
            try:
                response = requests.post(f"{OLLAMA_URL}{endpoint}", json=payload, timeout=60)
                response.raise_for_status()

                if "chat" in endpoint:
                    raw = response.json().get("message", {}).get("content", "").strip()
                else:
                    raw = response.json().get("response", "").strip()

                if raw:
                    break
            except requests.exceptions.Timeout:
                default["missing_info"] = "Local LLM timeout (>60s)"
                print("[LocalText] Timeout — inference exceeded 60s")
                return default
            except Exception as e:
                print(f"[LocalText] {endpoint} failed: {e}")
                continue

        if not raw:
            default["missing_info"] = "Empty response from local LLM"
            return default

        elapsed = time.time() - start_time
        print(f"[LocalText] Inference completed in {elapsed:.1f}s")

        # Debug output removed for production use

        # Strip markdown fences if present (same as Gemini module)
        if raw.startswith("```"):
            raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
            raw = re.sub(r"\n?```$", "", raw)
            raw = raw.strip()

        # Try to extract JSON from the response (Mistral might include explanatory text)
        # Look for JSON that may span multiple lines
        json_match = re.search(r'\{.*?\}', raw, re.DOTALL)
        if json_match:
            raw = json_match.group(0)
        else:
            print(f"[LocalText] No JSON found in response: {raw}")
            # If no JSON curly braces found, maybe it's just the JSON without extra text
            pass

        # Parse JSON response
        result = json.loads(raw)

        # Validate and clean up the response (same validation as Gemini module)
        match_result = str(result.get("match_result", "UNCERTAIN")).upper()
        if match_result not in ("YES", "LIKELY", "UNCERTAIN", "NO"):
            match_result = "UNCERTAIN"

        confidence = max(0, min(100, int(result.get("confidence", 0))))

        fitment = str(result.get("fitment_match", "UNKNOWN")).upper()
        if fitment not in ("YES", "NO", "UNKNOWN"):
            fitment = "UNKNOWN"

        desc = str(result.get("desc_match", "UNKNOWN")).upper()
        if desc not in ("YES", "NO", "PARTIAL", "UNKNOWN"):
            desc = "UNKNOWN"

        print(f"[LocalText] Result: {match_result} ({confidence}%)")

        return {
            "match_result":  match_result,
            "confidence":    confidence,
            "match_reason":  str(result.get("match_reason", ""))[:500],
            "fitment_match": fitment,
            "desc_match":    desc,
            "missing_info":  str(result.get("missing_info", ""))[:300],
        }

    except json.JSONDecodeError as e:
        default["missing_info"] = f"Local LLM JSON parse error: {e}"
        print(f"[LocalText] JSON parse error: {e}")
        return default

    except requests.exceptions.ConnectionError:
        _ollama_disabled = True
        default["missing_info"] = "Ollama not running. Start: ollama serve"
        print("[LocalText] Ollama not running — disabling for this session")
        return default

    except Exception as e:
        print(f"[LocalText] Error: {e}")
        default["missing_info"] = f"Local LLM error: {e}"
        return default


if __name__ == "__main__":
    # Quick test with the confirmed row 10 data (same as gemini_compare test)
    print("=" * 60)
    print("Local Text Comparison Test — Mistral 7B")
    print("=" * 60)

    # Check availability
    if not is_available():
        print("ERROR: Local text comparison not available")
        print("Run: ollama pull mistral")
        exit(1)

    print(f"Ollama: OK  (model: {_get_best_model()})")
    print()

    anchor = {
        "part_number": "3217", "brand": "ANCHOR", "found": True,
        "category": "Motor Mount", "oem_refs": ["5273883AD", "7B0199279A"],
        "price": "$20.79", "description": "Anchor Motor Mount", "features": [], "specs": {},
    }
    skp = {
        "part_number": "SKM3217", "brand": "SKP", "found": True,
        "category": "Motor Mount", "oem_refs": ["5273883AC", "5273883AD", "7B0199279"],
        "price": "$14.03", "description": "SKP Motor Mount", "features": [], "specs": {},
    }

    print("Testing ANCHOR 3217 vs SKP SKM3217 (ENGINE MOUNT)")
    result = compare_parts(anchor, skp, "ENGINE MOUNT",
                           rule_confidence=45, rule_reason="OEM base-number match only")
    print("\nResult:")
    print(json.dumps(result, indent=2))