"""
RockAuto scraper using Firecrawl API.

Searches RockAuto by part number, finds the specified brand's listing,
and extracts all available part data (category, OEM refs, specs, images).

Usage:
    result = await scrape_rockauto("3217",      brand="ANCHOR")
    result = await scrape_rockauto("SKM3217",   brand="SKP")
"""

import asyncio
import re
import json
from firecrawl import FirecrawlApp

FIRECRAWL_API_KEY = "fc-54a240ddf5824a3fa42b90d6a1ac1448"

# How long to wait (ms) for JS to render after form submit
SEARCH_WAIT_MS = 6000


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _scrape_search_page(app: FirecrawlApp, part_number: str) -> str:
    """
    Submit the RockAuto Part Number Search form and return the page markdown.
    Uses Firecrawl browser actions to fill and submit the form.
    """
    js_script = f"""
        var input = document.getElementById("partnum_partsearch_007");
        if (input) {{
            input.value = "{part_number}";
            input.dispatchEvent(new Event("change", {{bubbles:true}}));
        }}
        var btns = document.querySelectorAll("input[type=submit][value=Search]");
        for (var b of btns) {{
            if (b.id && b.id.includes("partsearch")) {{
                b.click();
                break;
            }}
        }}
    """
    result = app.scrape(
        "https://www.rockauto.com/en/partsearch/",
        formats=["markdown"],
        actions=[
            {"type": "wait", "milliseconds": 2000},
            {"type": "executeJavascript", "script": js_script},
            {"type": "wait", "milliseconds": SEARCH_WAIT_MS},
        ],
    )
    return getattr(result, "markdown", "") or ""


def _scrape_moreinfo_page(app: FirecrawlApp, moreinfo_url: str) -> str:
    """Fetch the moreinfo page for detailed specs and description."""
    result = app.scrape(moreinfo_url, formats=["markdown"])
    return getattr(result, "markdown", "") or ""


def _parse_listing(markdown: str, brand: str, part_number: str) -> dict:
    """
    Parse the search results markdown and extract data for the specified brand+part.
    Returns a dict with the extracted fields.
    """
    brand_upper = brand.upper()
    data = {
        "found": False,
        "category": None,
        "oem_refs": [],
        "image_url": None,
        "moreinfo_url": None,
        "price": None,
        "is_popular": False,
    }

    # Find the section containing our brand and part number
    # Pattern: "ANCHOR3217 [Info](...) Category: Motor Mount\n5273883AD, 7B0199279A"
    # Or: "SKP SKM3217 [Info](...)"

    # Search for the brand+partnumber block
    search_patterns = [
        rf"{re.escape(brand_upper)}\s*{re.escape(part_number)}",  # e.g. ANCHOR3217 or ANCHOR 3217
        rf"{re.escape(brand_upper)}{re.escape(part_number.replace('-', ''))}",  # without dashes
    ]

    idx = -1
    for pat in search_patterns:
        m = re.search(pat, markdown, re.IGNORECASE)
        if m:
            idx = m.start()
            break

    if idx < 0:
        return data

    data["found"] = True

    # Extract the 1500-char block after the brand match
    block = markdown[idx: idx + 1500]

    # Category — stop at <br>, |, or newline
    m_cat = re.search(r"Category:\s*([^<\n|\\]+)", block, re.IGNORECASE)
    if m_cat:
        data["category"] = _clean(m_cat.group(1))

    # OEM / interchange numbers (comma-separated on the line after Category)
    # They look like: "5273883AD, 7B0199279A"
    m_oem = re.search(
        r"Category:[^\n]+\n([A-Z0-9, ]+?)(?:\n|\||\[|$)",
        block,
        re.IGNORECASE,
    )
    if m_oem:
        raw_oem = m_oem.group(1)
        # Split by comma, filter to plausible OEM number format
        refs = [r.strip() for r in raw_oem.split(",")]
        refs = [r for r in refs if re.match(r"^[A-Z0-9]{4,}$", r)]
        data["oem_refs"] = refs

    # moreinfo URL (contains pk=XXXXXX)
    m_info = re.search(
        r"\(https://www\.rockauto\.com/en/moreinfo\.php\?pk=(\d+)[^)]+\)",
        block,
    )
    if m_info:
        data["moreinfo_url"] = (
            f"https://www.rockauto.com/en/moreinfo.php?pk={m_info.group(1)}&cc=0&pt=5552"
        )

    # Image URL
    m_img = re.search(
        r"!\[.*?\]\((https://www\.rockauto\.com/info/[^)]+__ra_m\.jpg)\)",
        block,
    )
    if m_img:
        data["image_url"] = m_img.group(1)

    # Price
    m_price = re.search(r"\$(\d+\.\d{2})", block)
    if m_price:
        data["price"] = f"${m_price.group(1)}"

    # Is popular
    if "most popular" in block.lower() or "Heart.png" in block:
        data["is_popular"] = True

    return data


def _parse_moreinfo(markdown: str) -> dict:
    """Extract specs, description, and OEM refs from the moreinfo page."""
    data = {
        "specs": {},
        "description": None,
        "features": [],
        "oem_refs": [],
        "warranty": None,
        "images": [],
    }

    # OEM / Interchange numbers
    m_oem = re.search(r"OEM\s*/\s*Interchange Numbers?:\s*([^\n|]+)", markdown, re.IGNORECASE)
    if m_oem:
        refs = [r.strip() for r in m_oem.group(1).split(",")]
        data["oem_refs"] = [r for r in refs if r]

    # Warranty
    m_warranty = re.search(r"Warranty Information:\s*([^\n|]+)", markdown, re.IGNORECASE)
    if m_warranty:
        data["warranty"] = _clean(m_warranty.group(1))

    # Specs table (e.g. "Mounting Hardware Included | No")
    spec_matches = re.findall(
        r"\|\s*([A-Z][^|]+?)\s*\|\s*(Yes|No|[0-9][^|]*?)\s*\|",
        markdown,
        re.IGNORECASE,
    )
    for key, val in spec_matches:
        key = _clean(key)
        val = _clean(val)
        if key and val and len(key) < 60:
            data["specs"][key] = val

    # Brand description / features (look for bold Features & Benefits section)
    m_desc = re.search(
        r"(Anchor Industries[^|]+?(?=\||\Z))",
        markdown,
        re.IGNORECASE | re.DOTALL,
    )
    if m_desc:
        desc_text = _clean(re.sub(r"<br>", " ", m_desc.group(1)))
        data["description"] = desc_text[:1000]

    # Features bullet points
    features = re.findall(r"- (.+?)(?:<br>|$)", markdown)
    data["features"] = [_clean(f) for f in features if len(f) > 10][:10]

    # Images
    images = re.findall(
        r"!\[.*?\]\((https://www\.rockauto\.com/info/\d+/[^)]+\.jpg)\)",
        markdown,
    )
    data["images"] = list(dict.fromkeys(images))[:5]

    return data


def scrape_rockauto(part_number: str, brand: str = "ANCHOR") -> dict:
    """
    Scrape RockAuto for a part number and extract data for a specific brand.

    Args:
        part_number: Part number to search (e.g. "3217" or "SKM3217")
        brand:       Brand to look for in results (e.g. "ANCHOR" or "SKP")

    Returns:
        dict with all extracted data
    """
    brand = brand.upper().strip()
    result = {
        "part_number":   part_number,
        "brand":         brand,
        "source":        "RockAuto",
        "search_url":    f"https://www.rockauto.com/en/partsearch/?partnum={part_number}",
        "found":         False,
        "blocked":       False,
        "category":      None,
        "oem_refs":      [],
        "image_url":     None,
        "moreinfo_url":  None,
        "price":         None,
        "specs":         {},
        "description":   None,
        "features":      [],
        "warranty":      None,
        "images":        [],
        "is_popular":    False,
        "error":         None,
    }

    try:
        app = FirecrawlApp(api_key=FIRECRAWL_API_KEY)

        # Step 1: Search for the part number
        print(f"[RockAuto] Searching for {part_number} (brand={brand})...")
        search_md = _scrape_search_page(app, part_number)

        if not search_md:
            result["error"] = "Empty response from Firecrawl"
            return result

        # Step 2: Parse the search results
        listing = _parse_listing(search_md, brand, part_number)

        if not listing["found"]:
            result["error"] = f"Brand '{brand}' not found in results for part '{part_number}'"
            return result

        # Merge listing data into result
        result.update({
            "found":        True,
            "category":     listing["category"],
            "oem_refs":     listing["oem_refs"],
            "image_url":    listing["image_url"],
            "moreinfo_url": listing["moreinfo_url"],
            "price":        listing["price"],
            "is_popular":   listing["is_popular"],
        })

        # Step 3: Fetch moreinfo page for additional specs
        if listing["moreinfo_url"]:
            print(f"[RockAuto] Fetching moreinfo for {brand} {part_number}...")
            moreinfo_md = _scrape_moreinfo_page(app, listing["moreinfo_url"])
            if moreinfo_md:
                info = _parse_moreinfo(moreinfo_md)
                result.update({
                    "specs":       info["specs"],
                    "description": info["description"],
                    "features":    info["features"],
                    "warranty":    info["warranty"],
                    "images":      info["images"],
                })
                # Prefer moreinfo OEM refs (more reliable)
                if info["oem_refs"]:
                    result["oem_refs"] = info["oem_refs"]

        print(f"[RockAuto] Done. Found: {result['found']}, Category: {result['category']}")
        return result

    except Exception as e:
        result["error"] = str(e)
        print(f"[RockAuto] Error: {e}")
        return result


if __name__ == "__main__":
    print("=" * 60)
    print("RockAuto Scraper Test — Powered by Firecrawl")
    print("=" * 60)

    # Test 1: Anchor 3217 (Engine Mount — row 10 of spreadsheet)
    print("\n--- Test 1: ANCHOR 3217 ---")
    r1 = scrape_rockauto("3217", brand="ANCHOR")
    print(json.dumps(r1, indent=2))

    # Small delay between requests
    import time
    time.sleep(3)

    # Test 2: SKP SKM3217 (same part, SKP brand)
    print("\n--- Test 2: SKP SKM3217 ---")
    r2 = scrape_rockauto("SKM3217", brand="SKP")
    print(json.dumps(r2, indent=2))
