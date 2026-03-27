"""
Google Gemini AI comparison module — free tier fallback.

Used when rule_compare gives an UNCERTAIN verdict (confidence 30–59%).
Gemini 1.5 Flash free tier: 1,500 requests/day, plenty for daily runs.

This module uses the same prompt and return schema as ai_compare.py
so it's a drop-in for uncertain cases.
"""

import re
import json
import os
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError

# Load .env from project root
_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    for _line in _env_path.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

GEMINI_MODEL = "gemini-3-flash-preview"

_client = None

# Set to True for the rest of this process run once daily quota is exhausted.
# Resets automatically on next run (new process = new session).
_quota_exhausted = False


def is_available() -> bool:
    """Returns False once the daily quota has been hit this session."""
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


def _build_prompt(anchor_data: dict, skp_data: dict, part_type: str,
                  rule_confidence: int, rule_reason: str) -> str:
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

Respond ONLY with valid JSON — no markdown fences, no text outside the JSON:

{{"match_result": "YES" | "LIKELY" | "UNCERTAIN" | "NO", "confidence": <integer 0-100>, "match_reason": "<1-2 sentences>", "fitment_match": "YES" | "NO" | "UNKNOWN", "desc_match": "YES" | "NO" | "PARTIAL", "missing_info": "<missing data or None>"}}"""


def compare_parts(anchor_data: dict, skp_data: dict, part_type: str,
                  rule_confidence: int = 0, rule_reason: str = "") -> dict:
    """
    Use Gemini to compare two parts when rules are uncertain.

    Args:
        anchor_data:      Dict from scrape_rockauto()
        skp_data:         Dict from scrape_rockauto()
        part_type:        Part type string from col A
        rule_confidence:  Confidence % from rule_compare (for context in prompt)
        rule_reason:      Reason string from rule_compare

    Returns same dict schema as rule_compare.compare_parts()
    """
    default = {
        "match_result":  "UNCERTAIN",
        "confidence":    0,
        "match_reason":  "Gemini comparison failed — see missing_info.",
        "fitment_match": "UNKNOWN",
        "desc_match":    "UNKNOWN",
        "missing_info":  "",
    }

    try:
        client = _get_client()
        prompt = _build_prompt(anchor_data, skp_data, part_type, rule_confidence, rule_reason)

        print(f"[Gemini] Comparing {anchor_data.get('part_number')} vs {skp_data.get('part_number')}...")

        from google.genai import types as gtypes
        _call_args = dict(
            model=GEMINI_MODEL,
            contents=[gtypes.Content(role="user", parts=[gtypes.Part.from_text(text=prompt)])],
        )
        with ThreadPoolExecutor(max_workers=1) as _ex:
            _future = _ex.submit(client.models.generate_content, **_call_args)
            try:
                response = _future.result(timeout=30)
            except FuturesTimeoutError:
                default["missing_info"] = "Gemini API timeout (>30s)"
                print("[Gemini] Timeout — API call exceeded 30s")
                return default
        raw = response.text.strip()

        # Strip markdown fences if present
        if raw.startswith("```"):
            raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
            raw = re.sub(r"\n?```$", "", raw)
            raw = raw.strip()

        result = json.loads(raw)

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

        print(f"[Gemini] Result: {match_result} ({confidence}%)")

        return {
            "match_result":  match_result,
            "confidence":    confidence,
            "match_reason":  str(result.get("match_reason", ""))[:500],
            "fitment_match": fitment,
            "desc_match":    desc,
            "missing_info":  str(result.get("missing_info", ""))[:300],
        }

    except json.JSONDecodeError as e:
        default["missing_info"] = f"Gemini JSON parse error: {e}"
        print(f"[Gemini] JSON parse error: {e}")
        return default
    except Exception as e:
        err_str = str(e)
        # Daily quota exhausted — disable Gemini for the rest of this session
        if "429" in err_str and "PerDay" in err_str:
            global _quota_exhausted
            _quota_exhausted = True
            print("[Gemini] Daily quota exhausted — switching to rules-only for this session.")
        else:
            print(f"[Gemini] Error: {e}")
        default["missing_info"] = f"Gemini error: {e}"
        return default


if __name__ == "__main__":
    # Quick test with the confirmed row 10 data
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
    result = compare_parts(anchor, skp, "ENGINE MOUNT",
                           rule_confidence=45, rule_reason="OEM base-number match only")
    print(json.dumps(result, indent=2))
