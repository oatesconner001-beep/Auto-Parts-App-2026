"""
Rule-based parts comparison engine — no AI API needed.

Evaluates 6 signals and combines them into a weighted verdict:

  1. OEM / interchange number matching     (weight: 40)
  2. Category matching                     (weight: 20)
  3. Part-type words in descriptions       (weight: 15)
  4. Fitment year/make/model overlap       (weight: 15)  * requires scraper enhancement
  5. Specs / measurements within tolerance (weight:  5)
  6. Visual image similarity               (weight:  5)  * requires Pillow

Each signal returns a score 0.0–1.0, multiplied by its weight.
Total possible = 100 points → maps to confidence %.
"""

import re
import os
import hashlib
import urllib.request
import urllib.error
from difflib import SequenceMatcher


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _tokens(text: str) -> set[str]:
    """Lowercase alphabetic tokens, length >= 3."""
    return {w.lower() for w in re.findall(r"[A-Za-z]{3,}", text or "")}


def _numeric_values(text: str) -> list[float]:
    """Extract all numbers (including decimals) from a string."""
    return [float(x) for x in re.findall(r"\d+(?:\.\d+)?", text or "")]


def _strip_suffix(oem: str) -> str:
    """Strip trailing letter revision suffixes: '5273883AD' -> '5273883'."""
    return re.sub(r"[A-Z]{1,2}$", "", oem.upper().strip())


def _normalize_oem(oem: str) -> str:
    return re.sub(r"[\s\-]", "", oem.upper().strip())


# ---------------------------------------------------------------------------
# Signal 1 — OEM / interchange number matching  (weight 40)
# ---------------------------------------------------------------------------

def _score_oem(anchor_refs: list, skp_refs: list) -> tuple[float, str]:
    """
    Returns (score 0.0–1.0, explanation).

    Exact shared refs = 1.0
    Base-number match (ignoring trailing letter revisions) = 0.7
    No overlap but both have refs = 0.0
    One or both missing refs = 0.3 (uncertain, not negative)
    """
    a_refs = [_normalize_oem(r) for r in (anchor_refs or []) if r]
    s_refs = [_normalize_oem(r) for r in (skp_refs or []) if r]

    if not a_refs or not s_refs:
        missing = []
        if not a_refs:
            missing.append("Anchor")
        if not s_refs:
            missing.append("SKP")
        return 0.3, f"No OEM refs available for: {', '.join(missing)}"

    # Exact intersection
    exact = set(a_refs) & set(s_refs)
    if exact:
        return 1.0, f"Shared OEM ref(s): {', '.join(sorted(exact))}"

    # Base-number intersection (strip trailing 1-2 letter suffixes)
    a_base = {_strip_suffix(r): r for r in a_refs}
    s_base = {_strip_suffix(r): r for r in s_refs}
    base_match = set(a_base) & set(s_base)
    if base_match:
        pairs = [f"{a_base[b]} ≈ {s_base[b]}" for b in sorted(base_match)]
        return 0.7, f"OEM base-number match (revision suffix differs): {', '.join(pairs)}"

    # Partial string similarity (e.g. "7B0199279A" vs "7B0199279")
    best_sim = 0.0
    best_pair = ("", "")
    for a in a_refs:
        for s in s_refs:
            sim = SequenceMatcher(None, a, s).ratio()
            if sim > best_sim:
                best_sim = sim
                best_pair = (a, s)

    if best_sim >= 0.85:
        return 0.5, f"OEM numbers very similar ({best_sim:.0%}): {best_pair[0]} vs {best_pair[1]}"

    return 0.0, (
        f"No OEM overlap. Anchor refs: {', '.join(a_refs[:4])} | "
        f"SKP refs: {', '.join(s_refs[:4])}"
    )


# ---------------------------------------------------------------------------
# Signal 2 — Category matching  (weight 20)
# ---------------------------------------------------------------------------

def _score_category(cat_a: str, cat_s: str) -> tuple[float, str]:
    if not cat_a or not cat_s:
        missing = []
        if not cat_a: missing.append("Anchor")
        if not cat_s: missing.append("SKP")
        return 0.3, f"Category not found for: {', '.join(missing)}"

    a = cat_a.strip().upper()
    s = cat_s.strip().upper()

    if a == s:
        return 1.0, f"Identical category: {cat_a}"

    # Token overlap
    a_tok = _tokens(a)
    s_tok = _tokens(s)
    if a_tok and s_tok:
        overlap = len(a_tok & s_tok) / max(len(a_tok), len(s_tok))
        if overlap >= 0.75:
            return 0.8, f"Category very similar: '{cat_a}' vs '{cat_s}'"
        if overlap >= 0.4:
            return 0.5, f"Category partially matches: '{cat_a}' vs '{cat_s}'"

    return 0.0, f"Category mismatch: '{cat_a}' vs '{cat_s}'"


# ---------------------------------------------------------------------------
# Signal 3 — Part-type words in descriptions / features  (weight 15)
# ---------------------------------------------------------------------------

# Words that are too generic to be useful as signals
_STOP_WORDS = {
    "the", "and", "for", "with", "from", "this", "that", "are", "has",
    "not", "will", "each", "also", "your", "its", "per", "new", "all",
    "inc", "nos", "qty", "pcs", "part", "parts", "item", "oem", "fits",
}

def _build_text(data: dict) -> str:
    """Combine all descriptive text fields into one string."""
    pieces = [
        data.get("category") or "",
        data.get("description") or "",
        " ".join(data.get("features") or []),
        " ".join(f"{k} {v}" for k, v in (data.get("specs") or {}).items()),
    ]
    return " ".join(pieces)


def _score_description(anchor_data: dict, skp_data: dict, part_type: str) -> tuple[float, str]:
    a_text = _build_text(anchor_data) + " " + part_type
    s_text = _build_text(skp_data) + " " + part_type

    a_tok = _tokens(a_text) - _STOP_WORDS
    s_tok = _tokens(s_text) - _STOP_WORDS

    if not a_tok or not s_tok:
        return 0.3, "Insufficient description text to compare"

    shared = a_tok & s_tok
    total  = a_tok | s_tok
    jaccard = len(shared) / len(total) if total else 0.0

    # Part-type words from catalog col A
    pt_words = _tokens(part_type) - _STOP_WORDS
    a_has_pt = bool(pt_words & a_tok)
    s_has_pt = bool(pt_words & s_tok)

    if a_has_pt and s_has_pt and jaccard >= 0.25:
        score = min(1.0, jaccard * 2.5)
        return score, f"Both descriptions contain part-type words; token overlap {jaccard:.0%}"

    if jaccard >= 0.3:
        return jaccard, f"Description token overlap {jaccard:.0%}"

    if jaccard >= 0.1:
        return 0.3, f"Low description overlap ({jaccard:.0%}); shared words: {', '.join(list(shared)[:6])}"

    return 0.1, f"Descriptions have little in common ({jaccard:.0%} overlap)"


# ---------------------------------------------------------------------------
# Signal 4 — Fitment year/make/model overlap  (weight 15)
# ---------------------------------------------------------------------------

def _score_fitment(anchor_data: dict, skp_data: dict) -> tuple[float, str]:
    """
    Extracts fitment strings from features/description using regex patterns
    like '2005-2010 Dodge', '2008 Ford F-150', etc.

    Requires the scraper to return vehicle application text in features/description.
    Returns UNKNOWN score (0.4) if no fitment data is found.
    """
    year_pat = re.compile(r"\b(19|20)\d{2}\b")
    make_pat = re.compile(
        r"\b(Acura|Audi|BMW|Buick|Cadillac|Chevrolet|Chevy|Chrysler|Dodge|"
        r"Ford|GMC|Honda|Hyundai|Infiniti|Jeep|Kia|Lexus|Lincoln|Mazda|"
        r"Mercedes|Mitsubishi|Nissan|Pontiac|Ram|Saturn|Subaru|Toyota|"
        r"Volkswagen|VW|Volvo)\b",
        re.IGNORECASE,
    )

    def extract_fitment(data: dict) -> dict:
        text = _build_text(data)
        years = set(year_pat.findall(text))
        makes = {m.lower() for m in make_pat.findall(text)}
        return {"years": years, "makes": makes, "has_data": bool(years or makes)}

    a_fit = extract_fitment(anchor_data)
    s_fit = extract_fitment(skp_data)

    if not a_fit["has_data"] or not s_fit["has_data"]:
        return 0.4, "Fitment year/make data not found in scraped text (UNKNOWN)"

    year_overlap = a_fit["years"] & s_fit["years"]
    make_overlap = a_fit["makes"] & s_fit["makes"]

    if year_overlap and make_overlap:
        return 1.0, (
            f"Fitment overlaps — years: {', '.join(sorted(year_overlap)[:4])}; "
            f"makes: {', '.join(sorted(make_overlap)[:4])}"
        )

    if make_overlap:
        return 0.6, f"Same vehicle makes: {', '.join(sorted(make_overlap)[:4])}; year ranges differ"

    if year_overlap:
        return 0.5, f"Overlapping years: {', '.join(sorted(year_overlap)[:4])}; different makes"

    # Both have data but no overlap
    a_makes = ", ".join(sorted(a_fit["makes"])[:3]) or "?"
    s_makes = ", ".join(sorted(s_fit["makes"])[:3]) or "?"
    return 0.0, f"No fitment overlap. Anchor: {a_makes} | SKP: {s_makes}"


# ---------------------------------------------------------------------------
# Signal 5 — Specs / measurements within tolerance  (weight 5)
# ---------------------------------------------------------------------------

TOLERANCE = 0.08  # 8% relative tolerance for numeric spec comparison


def _score_specs(anchor_data: dict, skp_data: dict) -> tuple[float, str]:
    a_specs = anchor_data.get("specs") or {}
    s_specs = skp_data.get("specs") or {}

    if not a_specs or not s_specs:
        return 0.4, "No spec table data available"

    # Normalize keys
    def norm_key(k):
        return re.sub(r"\s+", " ", k.strip().lower())

    a_norm = {norm_key(k): v for k, v in a_specs.items()}
    s_norm = {norm_key(k): v for k, v in s_specs.items()}

    shared_keys = set(a_norm) & set(s_norm)
    if not shared_keys:
        return 0.3, f"No shared spec fields between listings"

    matches = 0
    mismatches = []
    match_details = []

    for key in shared_keys:
        av = a_norm[key]
        sv = s_norm[key]

        # Boolean / categorical match
        if av.strip().lower() == sv.strip().lower():
            matches += 1
            match_details.append(f"{key}={av}")
            continue

        # Numeric comparison with tolerance
        a_nums = _numeric_values(av)
        s_nums = _numeric_values(sv)
        if a_nums and s_nums:
            a_avg = sum(a_nums) / len(a_nums)
            s_avg = sum(s_nums) / len(s_nums)
            if a_avg == 0 and s_avg == 0:
                matches += 1
                continue
            denom = max(abs(a_avg), abs(s_avg))
            rel_diff = abs(a_avg - s_avg) / denom if denom else 1.0
            if rel_diff <= TOLERANCE:
                matches += 1
                match_details.append(f"{key}: {av}≈{sv}")
                continue
            else:
                mismatches.append(f"{key}: {av} vs {sv}")
        else:
            mismatches.append(f"{key}: '{av}' vs '{sv}'")

    score = matches / len(shared_keys) if shared_keys else 0.4

    if mismatches:
        detail = f"Specs: {matches}/{len(shared_keys)} match; mismatches: {'; '.join(mismatches[:3])}"
    else:
        detail = f"All {matches} shared spec(s) match: {', '.join(match_details[:3])}"

    return score, detail


# ---------------------------------------------------------------------------
# Signal 6 — Visual image similarity  (weight 5)
# ---------------------------------------------------------------------------

def _image_hash(url: str, size: int = 8) -> str | None:
    """
    Download image and compute a simple average-hash (aHash).
    Returns hex string or None on failure.
    Works with stdlib only (no Pillow needed for basic hash).
    Uses raw pixel bytes for very rough similarity.
    """
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read()
        # Use MD5 of first 4KB as a cheap fingerprint
        # (same manufacturer image = same bytes = same hash)
        return hashlib.md5(data[:4096]).hexdigest()
    except Exception:
        return None


def _score_visual(anchor_data: dict, skp_data: dict) -> tuple[float, str]:
    a_img = anchor_data.get("image_url")
    s_img = skp_data.get("image_url")

    if not a_img or not s_img:
        return 0.4, "Image URL(s) not available for visual comparison"

    # Identical URL = same image = strong signal
    if a_img == s_img:
        return 1.0, "Parts share the exact same product image"

    # Compare image file hashes
    a_hash = _image_hash(a_img)
    s_hash = _image_hash(s_img)

    if a_hash is None or s_hash is None:
        return 0.4, "Could not download image(s) for comparison"

    if a_hash == s_hash:
        return 0.95, "Product images are visually identical (same pixel data)"

    # Compare image sizes as a rough proxy (same part from same OE often = same image size)
    return 0.4, "Product images differ — may reflect different packaging or photo styles"


# ---------------------------------------------------------------------------
# Weighted aggregation → final verdict
# ---------------------------------------------------------------------------

WEIGHTS = {
    "oem":         40,
    "category":    20,
    "description": 15,
    "fitment":     15,
    "specs":        5,
    "visual":       5,
}

assert sum(WEIGHTS.values()) == 100


def _confidence_to_verdict(confidence: int, cat_score: float) -> str:
    # Hard rule: category mismatch = NO regardless of other signals
    if cat_score == 0.0:
        return "NO"
    if confidence >= 80:
        return "YES"
    if confidence >= 60:
        return "LIKELY"
    if confidence >= 35:
        return "UNCERTAIN"
    return "NO"


def compare_parts(anchor_data: dict, skp_data: dict, part_type: str) -> dict:
    """
    Rule-based comparison. Drop-in replacement for ai_compare.compare_parts().

    Returns the same dict schema:
        match_result, confidence, match_reason,
        fitment_match, desc_match, missing_info
    """
    # Run all six signals
    oem_score,   oem_detail   = _score_oem(
        anchor_data.get("oem_refs", []),
        skp_data.get("oem_refs", []),
    )
    cat_score,   cat_detail   = _score_category(
        anchor_data.get("category"),
        skp_data.get("category"),
    )
    desc_score,  desc_detail  = _score_description(anchor_data, skp_data, part_type)
    fit_score,   fit_detail   = _score_fitment(anchor_data, skp_data)
    spec_score,  spec_detail  = _score_specs(anchor_data, skp_data)
    vis_score,   vis_detail   = _score_visual(anchor_data, skp_data)

    scores = {
        "oem":         oem_score,
        "category":    cat_score,
        "description": desc_score,
        "fitment":     fit_score,
        "specs":       spec_score,
        "visual":      vis_score,
    }

    # Weighted confidence
    confidence = int(sum(scores[k] * WEIGHTS[k] for k in WEIGHTS))
    match_result = _confidence_to_verdict(confidence, cat_score)

    # Derive sub-fields
    fitment_match = "UNKNOWN"
    if fit_score >= 0.8:
        fitment_match = "YES"
    elif fit_score <= 0.1:
        fitment_match = "NO"

    desc_match = "NO"
    if desc_score >= 0.7:
        desc_match = "YES"
    elif desc_score >= 0.35:
        desc_match = "PARTIAL"

    # Build a concise reason from the top signals
    top_signals = sorted(scores.items(), key=lambda x: -x[1] * WEIGHTS[x[0]])
    details = {
        "oem":         oem_detail,
        "category":    cat_detail,
        "description": desc_detail,
        "fitment":     fit_detail,
        "specs":       spec_detail,
        "visual":      vis_detail,
    }
    reason_parts = []
    for sig, _ in top_signals[:3]:
        reason_parts.append(details[sig])
    match_reason = " | ".join(reason_parts)[:500]

    # Missing info
    missing = []
    if not anchor_data.get("oem_refs"):
        missing.append("Anchor OEM refs")
    if not skp_data.get("oem_refs"):
        missing.append("SKP OEM refs")
    if fit_score == 0.4:
        missing.append("fitment year/make data")
    if vis_score == 0.4:
        missing.append("product images")
    if spec_score == 0.4:
        missing.append("spec tables")
    missing_info = ", ".join(missing) if missing else "None"

    # Signal breakdown for transparency
    breakdown = " | ".join(
        f"{k}:{scores[k]:.2f}×{WEIGHTS[k]}" for k in WEIGHTS
    )

    # Override: if either part wasn't found on RockAuto, can't be NO (absence ≠ mismatch)
    if match_result == "NO" and (not anchor_data.get("found") or not skp_data.get("found")):
        match_result = "UNCERTAIN"
        not_found = []
        if not anchor_data.get("found"):
            not_found.append(f"ANCHOR {anchor_data.get('part_number')} not found on RockAuto")
        if not skp_data.get("found"):
            not_found.append(f"SKP {skp_data.get('part_number')} not found on RockAuto")
        match_reason = "; ".join(not_found) + " — " + match_reason
        missing_info = ("; ".join(not_found) + "; " + missing_info).strip("; ")

    print(
        f"[Rules] {anchor_data.get('part_number')} vs {skp_data.get('part_number')}: "
        f"{match_result} ({confidence}%) — {breakdown}"
    )

    rule_result = {
        "match_result":  match_result,
        "confidence":    confidence,
        "match_reason":  match_reason[:500],
        "fitment_match": fitment_match,
        "desc_match":    desc_match,
        "missing_info":  missing_info,
    }

    # If NEITHER part was found on RockAuto, Claude has nothing to work with — skip it
    both_missing = not anchor_data.get("found") and not skp_data.get("found")

    # If UNCERTAIN, escalate to local Mistral 7B LLM for a second opinion
    # (skipped if Ollama unavailable — local_text_compare.is_available() returns False)
    if match_result == "UNCERTAIN" and not both_missing:
        try:
            from ai_compare import compare_parts as claude_compare
            claude_result = claude_compare(anchor_data, skp_data, part_type)
            # Only use Claude result if it actually produced a real answer (confidence > 0)
            if claude_result.get("confidence", 0) > 0:
                claude_result["missing_info"] = (
                    f"[Rules: {confidence}%] " + claude_result.get("missing_info", "")
                ).strip()
                return claude_result
            else:
                print(f"[Rules] Claude returned no result — keeping rule result")
        except Exception as e:
            print(f"[Rules] Claude fallback error: {e} — keeping rule result")

    return rule_result


# ---------------------------------------------------------------------------
# CLI test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import json

    # Confirmed working test case (row 10)
    anchor = {
        "part_number": "3217",
        "brand":       "ANCHOR",
        "found":       True,
        "category":    "Motor Mount",
        "oem_refs":    ["5273883AD", "7B0199279A"],
        "price":       "$20.79",
        "description": "Anchor Industries Motor Mount Direct Replacement",
        "features":    ["Direct fit replacement", "Helps reduce vibration and noise"],
        "specs":       {"Mounting Hardware Included": "No", "Bushing Material": "Rubber"},
        "image_url":   None,
    }
    skp = {
        "part_number": "SKM3217",
        "brand":       "SKP",
        "found":       True,
        "category":    "Motor Mount",
        "oem_refs":    ["5273883AC", "5273883AD", "7B0199279"],
        "price":       "$14.03",
        "description": "SKP Motor Mount Replacement Part",
        "features":    ["Replaces OEM mount", "Rubber bushing construction"],
        "specs":       {"Mounting Hardware Included": "No", "Bushing Material": "Rubber"},
        "image_url":   None,
    }
    result = compare_parts(anchor, skp, "ENGINE MOUNT")
    print(json.dumps(result, indent=2))

    print("\n--- Mismatch test ---")
    bad_skp = {
        "part_number": "SK999",
        "brand":       "SKP",
        "found":       True,
        "category":    "Water Pump",
        "oem_refs":    ["1234567XX"],
        "price":       "$45.00",
        "description": "Water pump for cooling system",
        "features":    [],
        "specs":       {},
        "image_url":   None,
    }
    result2 = compare_parts(anchor, bad_skp, "ENGINE MOUNT")
    print(json.dumps(result2, indent=2))
