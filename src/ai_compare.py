"""
Claude AI comparison module.

Sends both parts' scraped data to Claude and gets a structured match verdict.
"""

import re
import json
import os
from pathlib import Path
import anthropic

# Load .env from project root (one level up from src/)
_env_path = Path(__file__).parent.parent / ".env"
if _env_path.exists():
    for _line in _env_path.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

MODEL = "claude-sonnet-4-20250514"

_client = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env
    return _client


def _build_prompt(anchor_data: dict, skp_data: dict, part_type: str) -> str:
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
            lines.append(f"  Description: {d['description'][:500]}")
        if d.get("features"):
            lines.append(f"  Features: {'; '.join(d['features'][:5])}")
        if d.get("specs"):
            specs_str = "; ".join(f"{k}={v}" for k, v in list(d["specs"].items())[:6])
            lines.append(f"  Specs: {specs_str}")
        if d.get("warranty"):
            lines.append(f"  Warranty: {d['warranty']}")
        if d.get("error"):
            lines.append(f"  Error/Not found reason: {d['error']}")
        return "\n".join(lines)

    return f"""You are an automotive parts compatibility expert. Determine whether two auto parts are interchangeable matches.

PART TYPE (from buyer's catalog): {part_type}

ANCHOR PART:
{fmt(anchor_data)}

SKP PART:
{fmt(skp_data)}

MATCHING RULES (in order of strength):
1. Shared OEM/interchange numbers = STRONGEST signal. If both parts list the same OEM number, they almost certainly fit the same vehicle application.
2. Same category = necessary but not sufficient on its own.
3. Similar descriptions/features = supporting evidence.
4. Price difference alone is NOT evidence of mismatch.
5. If one part was NOT FOUND on RockAuto, result must be UNCERTAIN (not NO) — absence of data ≠ mismatch.

Respond ONLY with a valid JSON object — no markdown fences, no explanation outside JSON:

{{
  "match_result": "YES" | "LIKELY" | "UNCERTAIN" | "NO",
  "confidence": <integer 0-100>,
  "match_reason": "<1-2 sentences explaining the verdict>",
  "fitment_match": "YES" | "NO" | "UNKNOWN",
  "desc_match": "YES" | "NO" | "PARTIAL",
  "missing_info": "<what data was unavailable or would strengthen confidence, or 'None'>"
}}

Guidelines for match_result:
- YES (85-100): Confirmed match — shared OEM ref(s) and/or identical specs/fitment
- LIKELY (60-84): Strong indicators align but not fully confirmed
- UNCERTAIN (30-59): Insufficient data or conflicting signals
- NO (0-29): Clear mismatch in category, fitment, or specs"""


def compare_parts(anchor_data: dict, skp_data: dict, part_type: str) -> dict:
    """
    Compare an ANCHOR part against a SKP part using Claude AI.

    Args:
        anchor_data: Dict returned by scrape_rockauto() for the ANCHOR part
        skp_data:    Dict returned by scrape_rockauto() for the SKP part
        part_type:   Part type string from col A of the spreadsheet

    Returns:
        dict with keys: match_result, confidence, match_reason,
                        fitment_match, desc_match, missing_info
    """
    default = {
        "match_result": "UNCERTAIN",
        "confidence": 0,
        "match_reason": "AI comparison failed — see missing_info.",
        "fitment_match": "UNKNOWN",
        "desc_match": "UNKNOWN",
        "missing_info": "",
    }

    try:
        prompt = _build_prompt(anchor_data, skp_data, part_type)
        client = _get_client()

        print(f"[AI] Comparing {anchor_data.get('part_number')} vs {skp_data.get('part_number')}...")

        message = client.messages.create(
            model=MODEL,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )

        raw = message.content[0].text.strip()

        # Strip any accidental markdown fences
        if raw.startswith("```"):
            raw = re.sub(r"^```[a-zA-Z]*\n?", "", raw)
            raw = re.sub(r"\n?```$", "", raw)
            raw = raw.strip()

        result = json.loads(raw)

        # Validate and coerce fields
        match_result = str(result.get("match_result", "UNCERTAIN")).upper()
        if match_result not in ("YES", "LIKELY", "UNCERTAIN", "NO"):
            match_result = "UNCERTAIN"

        confidence = int(result.get("confidence", 0))
        confidence = max(0, min(100, confidence))

        fitment = str(result.get("fitment_match", "UNKNOWN")).upper()
        if fitment not in ("YES", "NO", "UNKNOWN"):
            fitment = "UNKNOWN"

        desc = str(result.get("desc_match", "UNKNOWN")).upper()
        if desc not in ("YES", "NO", "PARTIAL", "UNKNOWN"):
            desc = "UNKNOWN"

        print(f"[AI] Result: {match_result} ({confidence}%)")

        return {
            "match_result":  match_result,
            "confidence":    confidence,
            "match_reason":  str(result.get("match_reason", ""))[:500],
            "fitment_match": fitment,
            "desc_match":    desc,
            "missing_info":  str(result.get("missing_info", ""))[:300],
        }

    except json.JSONDecodeError as e:
        default["missing_info"] = f"JSON parse error: {e}"
        print(f"[AI] JSON parse error: {e}")
        return default
    except Exception as e:
        default["missing_info"] = f"Error: {e}"
        print(f"[AI] Error: {e}")
        return default


if __name__ == "__main__":
    # Quick test using the confirmed row 10 data
    anchor = {
        "part_number": "3217",
        "brand": "ANCHOR",
        "found": True,
        "category": "Motor Mount",
        "oem_refs": ["5273883AD", "7B0199279A"],
        "price": "$20.79",
        "description": "Anchor Industries Motor Mount",
        "features": [],
        "specs": {},
    }
    skp = {
        "part_number": "SKM3217",
        "brand": "SKP",
        "found": True,
        "category": "Motor Mount",
        "oem_refs": ["5273883AC", "5273883AD", "7B0199279"],
        "price": "$14.03",
        "description": "SKP Motor Mount",
        "features": [],
        "specs": {},
    }
    result = compare_parts(anchor, skp, "ENGINE MOUNT")
    print(json.dumps(result, indent=2))
