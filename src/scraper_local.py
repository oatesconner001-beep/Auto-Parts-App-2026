"""
Local RockAuto scraper — free replacement for Firecrawl.

Uses Playwright with the user's REAL Chrome browser (not headless Chromium).
Connects to a persistent browser profile so RockAuto sees a real returning visitor.
The key difference from previous failed attempts:
  - channel="chrome"  → real Chrome binary, not Chromium
  - headless=False    → visible window, no headless signals
  - persistent profile → cookies/history accumulate over time
  - stealth patches   → removes navigator.webdriver and automation signals
  - ignore_default_args → suppresses --enable-automation flag Chrome adds

Same return dict schema as scraper_rockauto.py — drop-in replacement.
"""

import re
import json
import time
import subprocess
from pathlib import Path

# Unicode safety utilities
import sys
sys.path.insert(0, str(Path(__file__).parent))
from unicode_utils import sanitize_unicode_dict, sanitize_unicode_text

# Persistent browser profile so RockAuto treats us as a returning user
import tempfile
import uuid
PROFILE_DIR = str(Path(tempfile.gettempdir()) / f"browser_profile_{uuid.uuid4().hex[:8]}")

SEARCH_URL   = "https://www.rockauto.com/en/partsearch/"
SEARCH_WAIT  = 7000   # ms to wait after form submit for JS to render
CAPTCHA_WAIT = 60     # seconds to wait if CAPTCHA appears (user solves manually)

# Restart Chrome every N calls to prevent session degradation
# Based on testing: degradation occurs around call 37, restart at 30 for safety margin
RESTART_EVERY = 30

# Module-level browser context — stays open across multiple scrape() calls
_pw      = None   # sync_playwright() instance — must be stopped on close() to end event loop
_context = None
_page    = None
_call_count = 0


def _clear_profile_lock():
    """
    Remove Chrome's lockfile from the profile directory if it is stale.
    Checks whether any Chrome process actually uses our profile directory;
    if not, forcefully removes the lock via PowerShell (bash rm fails on Windows).
    """
    lock_path = Path(PROFILE_DIR) / "lockfile"
    if not lock_path.exists():
        return

    # Check if any Chrome process has our profile path in its command line
    profile_abs = str(Path(PROFILE_DIR).resolve()).replace("\\", "\\\\")
    try:
        result = subprocess.run(
            ["powershell", "-Command",
             f"(Get-CimInstance Win32_Process | Where-Object "
             f"{{$_.Name -eq 'chrome.exe' -and $_.CommandLine -like '*browser_profile*'}}).Count"],
            capture_output=True, text=True, timeout=8
        )
        count = result.stdout.strip()
        if count == "0" or count == "":
            # No Chrome using our profile — safe to remove lock
            subprocess.run(
                ["powershell", "-Command",
                 f"Remove-Item '{lock_path}' -Force -ErrorAction SilentlyContinue"],
                timeout=5
            )
            print("[Local] Cleared stale Chrome profile lockfile.")
    except Exception:
        pass


def _launch_browser():
    """Launch a fresh Chrome persistent context and return the first page."""
    global _pw, _context, _page

    _clear_profile_lock()

    from playwright.sync_api import sync_playwright
    try:
        from playwright_stealth import stealth_sync
        _has_stealth = True
    except ImportError:
        _has_stealth = False

    _pw = sync_playwright().start()

    _context = _pw.chromium.launch_persistent_context(
        user_data_dir=PROFILE_DIR,
        channel="chrome",           # real Chrome, not Chromium
        headless=True,              # headless for stability
        slow_mo=50,                 # slight humanisation
        args=[
            "--disable-blink-features=AutomationControlled",
            "--disable-infobars",
            "--window-position=-32000,-32000",
            "--window-size=100,100",
        ],
        ignore_default_args=["--enable-automation"],
        viewport=None,              # use window size, not fixed viewport
    )

    _page = _context.new_page() if not _context.pages else _context.pages[0]

    if _has_stealth:
        stealth_sync(_page)

    return _page


def _get_page():
    """Return a live Playwright page, launching browser if needed."""
    global _pw, _context, _page, _call_count

    # Check for existing asyncio event loop and handle gracefully
    import asyncio
    try:
        loop = asyncio.get_running_loop()
        if loop.is_running():
            # There's an active asyncio loop - we need to run in a thread
            print("[Local] Detected asyncio loop, running Playwright in thread...")
            import threading
            import queue

            result_queue = queue.Queue()
            error_queue = queue.Queue()

            def run_playwright_in_thread():
                try:
                    page = _get_page_sync()
                    result_queue.put(page)
                except Exception as e:
                    error_queue.put(e)

            thread = threading.Thread(target=run_playwright_in_thread)
            thread.start()
            thread.join(timeout=30)  # 30 second timeout

            if not result_queue.empty():
                return result_queue.get()
            elif not error_queue.empty():
                raise error_queue.get()
            else:
                raise Exception("Playwright thread timed out")

    except RuntimeError:
        # No asyncio loop running, proceed normally
        pass

    return _get_page_sync()

def _get_page_sync():
    """Synchronous version of _get_page for thread isolation."""
    global _pw, _context, _page, _call_count

    if _page is not None:
        try:
            _page.title()   # ping — raises if browser closed
            return _page
        except Exception:
            # Browser went away — clean up completely so we can restart fresh
            try:
                if _context: _context.close()
            except Exception:
                pass
            try:
                if _pw: _pw.stop()
            except Exception:
                pass
            _pw = None
            _context = None
            _page = None
            time.sleep(5)   # Give asyncio event loop time to fully shut down

    return _launch_browser()


def _wait_past_captcha(page) -> bool:
    """
    If we land on a CAPTCHA page, wait up to CAPTCHA_WAIT seconds for the
    user to solve it manually. Returns True if we got through.
    """
    for _ in range(CAPTCHA_WAIT):
        url = page.url
        if "/captcha/" not in url and "challenge" not in url.lower():
            return True
        time.sleep(1)
    return False


def _get_page_text(page) -> str:
    """Get the rendered text content of the current page."""
    try:
        return page.inner_text("body") or ""
    except Exception:
        return ""


def _scrape_search(page, part_number: str) -> str:
    """Navigate to RockAuto part search, submit the form, return page text."""
    try:
        page.goto(SEARCH_URL, wait_until="domcontentloaded", timeout=30000)
    except Exception as e:
        return f"__NAV_ERROR__: {e}"

    if not _wait_past_captcha(page):
        return "__CAPTCHA__"

    # Wait for the form to be ready
    try:
        page.wait_for_selector("#partnum_partsearch_007", timeout=10000)
    except Exception:
        pass

    # Fill and submit the form via JavaScript (same approach as Firecrawl)
    page.evaluate(f"""
        var input = document.getElementById("partnum_partsearch_007");
        if (input) {{
            input.value = "{part_number}";
            input.dispatchEvent(new Event("change", {{bubbles: true}}));
        }}
        var btns = document.querySelectorAll("input[type=submit][value=Search]");
        for (var b of btns) {{
            if (b.id && b.id.includes("partsearch")) {{
                b.click();
                break;
            }}
        }}
    """)

    # Wait for JS to render results
    page.wait_for_timeout(SEARCH_WAIT)

    # Wait specifically for price elements to have content
    try:
        page.wait_for_function(
            """() => {
                const elems = document.querySelectorAll(
                    "span[id*='dprice'][id*='[v]']"
                );
                return elems.length > 0 &&
                       elems[0].textContent.trim().length > 0;
            }""",
            timeout=10000
        )
    except Exception:
        pass  # Continue even if timeout - price may still be extractable

    if not _wait_past_captcha(page):
        return "__CAPTCHA__"

    return _get_page_text(page)


def _scrape_moreinfo(page, url: str) -> str:
    """Fetch a moreinfo page and return its text."""
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=20000)
        _wait_past_captcha(page)
        page.wait_for_timeout(2000)
        return _get_page_text(page)
    except Exception as e:
        return ""


def _clean(text: str) -> str:
    """Clean and sanitize text using Unicode utilities"""
    if not text:
        return ""
    try:
        cleaned = re.sub(r"\s+", " ", text).strip()
        return sanitize_unicode_text(cleaned)
    except Exception:
        return sanitize_unicode_text(text or "")


def _extract_fitment_from_url(url: str) -> dict:
    """
    Extract vehicle fitment from RockAuto catalog URL.
    URL format: /catalog/make,year,model,engine,category_id,section,part_type,part_id
    """
    fitment = {}
    try:
        if '/catalog/' in url:
            path_parts = url.split('/catalog/')[-1].split(',')
            if len(path_parts) >= 4:
                fitment = {
                    "make": sanitize_unicode_text(path_parts[0].replace('+', ' ').title()),
                    "year": int(path_parts[1]) if path_parts[1].isdigit() else None,
                    "model": sanitize_unicode_text(path_parts[2].replace('+', ' ').title()),
                    "engine": sanitize_unicode_text(path_parts[3].replace('+', ' ').upper()) if len(path_parts) > 3 else None
                }
    except Exception:
        pass

    return sanitize_unicode_dict(fitment)


# OEM reference validation — filters out warranty text, UI strings, and garbage
_OEM_BLACKLIST = {"INCLUDES", "THERMOSTAT", "WARRANTY", "INFORMATION", "DETAILS",
                  "MONTHS", "MILES", "LIMITED", "LIFETIME", "PLEASE", "CONTACT",
                  "NUMBER", "RETURN", "POLICY"}

def _is_valid_oem_ref(ref: str) -> bool:
    """Validate that a string looks like a real OEM part number (6-15 alphanumeric chars, no spaces)."""
    ref = ref.strip()
    if not ref or ' ' in ref:
        return False
    if len(ref) < 6 or len(ref) > 15:
        return False
    if not re.match(r'^[A-Z0-9\-]+$', ref, re.IGNORECASE):
        return False
    if ref.upper() in _OEM_BLACKLIST:
        return False
    return True


def _parse_alternate_oem_refs(page) -> list:
    """
    Parse OEM references from verified HTML structure:
    <section aria-label="Alternate/OEM Part Number(s)">
    Format: {Alternate Inventory Numbers: PARTNUMBER:VARIANT}
    """
    oem_refs = []
    try:
        oem_sections = page.query_selector_all('section[aria-label*="Alternate/OEM Part Number"]')
        for section in oem_sections:
            text = section.inner_text()
            # Parse format: {Alternate Inventory Numbers: POF4006:8}
            if "Alternate Inventory Numbers:" in text:
                # Extract part numbers after the colon, strip curly braces
                parts_text = text.split("Alternate Inventory Numbers:")[-1]
                parts_text = re.sub(r'[{}]', '', parts_text).strip()

                # Extract alphanumeric part numbers
                refs = re.findall(r'\b([A-Z0-9]{4,})\b', parts_text.upper())
                for ref in refs:
                    if len(ref) >= 4:  # Minimum OEM reference length
                        oem_refs.append({
                            "oem_number": sanitize_unicode_text(ref),
                            "reference_type": "ALTERNATE"
                        })
    except Exception:
        pass

    return oem_refs[:10]  # Limit to prevent overflow


def _parse_warranty_notes(page) -> dict:
    """
    Extract warranty information and notes from listing-text-row elements
    and warranty table sections as verified in HTML structure
    """
    data = {"warranty": None, "notes": []}

    try:
        # Extract from listing-text-row divs (verified structure)
        text_rows = page.query_selector_all('div.listing-text-row')
        for row in text_rows:
            text = _clean(row.inner_text())
            if text and len(text) > 10:
                # Check if it's warranty information
                if any(keyword in text.lower() for keyword in ['warranty', 'closeout', 'return policy']):
                    data["warranty"] = text[:200]  # Limit length
                else:
                    data["notes"].append(text[:150])  # Limit note length

        # Extract from warranty table (verified structure)
        warranty_tables = page.query_selector_all('table.warranty')
        for table in warranty_tables:
            warranty_text = _clean(table.inner_text())
            if warranty_text and "warranty" in warranty_text.lower():
                data["warranty"] = warranty_text[:300]  # More space for warranty details
                break

    except Exception:
        pass

    # Limit notes count and sanitize
    data["notes"] = data["notes"][:5]  # Max 5 notes
    data["warranty"] = sanitize_unicode_text(data["warranty"]) if data["warranty"] else None
    data["notes"] = [sanitize_unicode_text(note) for note in data["notes"]]

    return data


def _get_all_product_images(page) -> list:
    """
    Extract ALL product image URLs from a loaded moreinfo page.
    RockAuto product images live at URLs like:
        https://www.rockauto.com/info/28/3217-000__ra_m.jpg
    """
    images = []
    try:
        imgs = page.query_selector_all("img[src*='/info/']")
        for img in imgs:
            src = img.get_attribute("src") or ""
            if src:
                # Convert relative URLs to absolute
                if src.startswith("/"):
                    src = "https://www.rockauto.com" + src

                # Determine image type based on filename patterns
                image_type = "product"
                if "ra_s" in src:
                    image_type = "thumbnail"
                elif "ra_l" in src:
                    image_type = "large"
                elif "ra_m" in src:
                    image_type = "medium"
                elif "_diagram" in src or "diag" in src:
                    image_type = "diagram"

                images.append({
                    "url": sanitize_unicode_text(src),
                    "type": image_type,
                    "is_primary": len(images) == 0  # First image is primary
                })

        # Remove duplicates while preserving order
        seen_urls = set()
        unique_images = []
        for img in images:
            if img["url"] not in seen_urls:
                seen_urls.add(img["url"])
                unique_images.append(img)

    except Exception:
        pass

    return unique_images[:10]  # Limit to 10 images max


def _parse_listing(text: str, brand: str, part_number: str, extracted_data: dict = None) -> dict:
    """
    Parse search result page text for the target brand+part listing.
    RockAuto's rendered text looks like:
        ANCHOR 3217   Info
        Motor Mount
        5273883AD, 7B0199279A
        $20.79
    """
    data = {
        "found": False, "category": None, "oem_refs": [],
        "image_url": None, "moreinfo_url": None, "price": None, "core_charge": None,
        "is_popular": False, "listing_id": None,
    }

    # Use extracted data as overrides if available
    if extracted_data:
        data["price"] = extracted_data.get("price") or data["price"]
        data["core_charge"] = extracted_data.get("core_charge") or data["core_charge"]
        data["category"] = extracted_data.get("category") or data["category"]

    brand_upper = brand.upper()
    pnum_clean  = re.sub(r"[\s\-]", "", part_number).upper()

    # Find brand+partnumber in text (with or without dash/space)
    patterns = [
        rf"{re.escape(brand_upper)}\s*{re.escape(part_number)}",
        rf"{re.escape(brand_upper)}\s*{re.escape(pnum_clean)}",
        rf"{re.escape(brand_upper)}{re.escape(pnum_clean)}",
    ]

    idx = -1
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            idx = m.start()
            break

    if idx < 0:
        return data

    data["found"] = True
    data["listing_id"] = "text_0"  # Default listing ID for text-based parsing
    block = text[idx: idx + 2000]

    # Category fallback if not extracted at page level
    if not data["category"]:
        m = re.search(r"(?:Motor Mount|Water Pump|Valve Cover|Oil Pan|Blower Motor|"
                      r"Door Lock|Engine Mount|Timing|[A-Z][a-z]+ [A-Z][a-z]+)", block)
        if not m:
            # Fallback: look for "Category:" label
            m = re.search(r"Category[:\s]+([^\n]{3,50})", block, re.IGNORECASE)
            if m:
                data["category"] = _clean(m.group(1))
        else:
            data["category"] = _clean(m.group(0))

    # OEM / interchange refs — alphanumeric tokens 6+ chars after the category line
    if not data.get("oem_refs"):
        oem_block = block[:500]
        # Strip anything after Warranty keyword to avoid warranty text as OEM refs
        warranty_idx = oem_block.upper().find("WARRANTY")
        if warranty_idx > 0:
            oem_block = oem_block[:warranty_idx]
        refs = re.findall(r"\b([A-Z0-9]{6,})\b", oem_block)
        # Filter: not the part number itself, not common words
        skip = {pnum_clean, brand_upper, "SEARCH", "RESULT", "ANCHOR", "DORMAN",
                "FILTER", "SORTBY", "VEHICLE", "CATALOG"}
        data["oem_refs"] = [{"oem_number": sanitize_unicode_text(r), "reference_type": "OEM"}
                           for r in refs if r not in skip and not r.startswith("SK") and _is_valid_oem_ref(r)][:8]

    # Price fallback if not extracted at page level
    if not data["price"]:
        m = re.search(r"\$(\d+\.\d{2})", block)
        if m:
            data["price"] = sanitize_unicode_text(f"${m.group(1)}")

    if "popular" in block.lower():
        data["is_popular"] = True

    return sanitize_unicode_dict(data)


def _parse_all_listings_html(page, brand: str, part_number: str, extracted_data: dict = None) -> list:
    """
    Extract ALL listings for a part, not just the first one.
    Returns list of listing dictionaries with unique listing_ids.
    """
    listings = []
    brand_upper = brand.upper()
    pnum_norm = re.sub(r"[\s\-]", "", part_number).upper()

    try:
        # Find all moreinfo links on the page
        links = page.query_selector_all("a[href*='moreinfo.php']")

        for i, link in enumerate(links):
            href = link.get_attribute("href") or ""

            # Get surrounding text to check if this is our brand/part
            parent_text = ""
            try:
                container = link.evaluate(
                    "el => el.closest('tr, .listing-col-wrap, [class*=\"listing\"], div') "
                    "? el.closest('tr, .listing-col-wrap, [class*=\"listing\"], div').innerText : ''"
                )
                parent_text = sanitize_unicode_text(container or "").upper()
            except Exception:
                continue

            brand_in_text = brand_upper in parent_text
            part_in_text = (part_number.upper() in parent_text or
                           pnum_norm in re.sub(r"[\s\-]", "", parent_text))

            if brand_in_text and part_in_text:
                listing_data = {
                    "found": True,
                    "listing_id": f"dom_{i}",  # Unique listing ID
                    "category": None,
                    "oem_refs": [],
                    "image_url": None,
                    "moreinfo_url": None,
                    "price": None,
                    "core_charge": None,
                    "is_popular": False,
                }

                # Use extracted data as overrides (price/category for first listing, core_charge for all)
                if extracted_data:
                    if i == 0:
                        listing_data["price"] = extracted_data.get("price") or listing_data["price"]
                        listing_data["category"] = extracted_data.get("category") or listing_data["category"]
                    listing_data["core_charge"] = extracted_data.get("core_charge") or listing_data["core_charge"]

                # Set moreinfo URL
                if href.startswith("/"):
                    listing_data["moreinfo_url"] = "https://www.rockauto.com" + href
                else:
                    listing_data["moreinfo_url"] = href

                # Extract OEM refs and price from the container text if not already set
                if not listing_data.get("oem_refs"):
                    # Strip anything after Warranty keyword
                    clean_text = parent_text
                    warranty_idx = clean_text.find("WARRANTY")
                    if warranty_idx > 0:
                        clean_text = clean_text[:warranty_idx]
                    refs = re.findall(r"\b([A-Z0-9]{6,})\b", clean_text)
                    skip = {brand_upper, pnum_norm, "SEARCH", "MOREINFO", "FILTER", "VEHICLE", "CATALOG"}
                    listing_data["oem_refs"] = [{"oem_number": sanitize_unicode_text(r), "reference_type": "OEM"}
                                               for r in refs if r not in skip and _is_valid_oem_ref(r)][:8]

                # Extract price if not already set
                if not listing_data["price"]:
                    m = re.search(r"\$(\d+\.\d{2})", parent_text)
                    if m:
                        listing_data["price"] = sanitize_unicode_text(f"${m.group(1)}")

                if "popular" in parent_text.lower():
                    listing_data["is_popular"] = True

                # Try to extract category from the part type heading above this listing
                if not listing_data["category"]:
                    try:
                        cat = link.evaluate("""el => {
                            var node = el;
                            for (var i = 0; i < 10; i++) {
                                node = node.parentElement;
                                if (!node) break;
                                var heading = node.querySelector('[class*="parttype"], [class*="category"], h2, h3');
                                if (heading && heading.innerText.trim().length > 2)
                                    return heading.innerText.trim();
                            }
                            return '';
                        }""")
                        if cat:
                            listing_data["category"] = sanitize_unicode_text(cat.split("\n")[0].strip())
                    except Exception:
                        pass

                listings.append(sanitize_unicode_dict(listing_data))

    except Exception:
        pass

    return listings


def _parse_listing_html(page, brand: str, part_number: str, extracted_data: dict = None) -> dict:
    """
    Use Playwright DOM queries to find the brand listing and extract
    the moreinfo href more reliably than text parsing.
    Returns the FIRST listing found (backward compatibility).
    """
    # Get all listings and return the first one for backward compatibility
    listings = _parse_all_listings_html(page, brand, part_number, extracted_data)

    if listings:
        return listings[0]

    # Return empty result if no listings found
    return {
        "found": False, "category": None, "oem_refs": [],
        "image_url": None, "moreinfo_url": None, "price": None, "core_charge": None,
        "is_popular": False, "listing_id": None,
    }


def _get_moreinfo_image_url(page) -> str | None:
    """
    Extract the main product image URL from a loaded moreinfo page.
    RockAuto product images live at URLs like:
        https://www.rockauto.com/info/28/3217-000__ra_m.jpg
    We query for <img> tags whose src contains '/info/' and ends with a
    known RockAuto image suffix.
    """
    try:
        imgs = page.query_selector_all("img[src*='/info/']")
        for img in imgs:
            src = img.get_attribute("src") or ""
            # Skip tiny icons / logos (ra_m = medium product image)
            if "ra_m" in src or "ra_l" in src or "_1_" in src:
                if src.startswith("/"):
                    return sanitize_unicode_text("https://www.rockauto.com" + src)
                return sanitize_unicode_text(src)
        # Fallback: any /info/ image
        for img in imgs:
            src = img.get_attribute("src") or ""
            if src:
                if src.startswith("/"):
                    return sanitize_unicode_text("https://www.rockauto.com" + src)
                return sanitize_unicode_text(src)
    except Exception:
        pass
    return None


def _parse_moreinfo_text(text: str) -> dict:
    """Parse moreinfo page text — same patterns as scraper_rockauto._parse_moreinfo."""
    data = {
        "specs": {}, "description": None, "features": [],
        "oem_refs": [], "warranty": None, "images": [],
    }

    # Apply Unicode sanitization to input text
    text = sanitize_unicode_text(text)

    # OEM / Interchange numbers
    m = re.search(r"OEM\s*/?\s*Interchange Numbers?:?\s*([^\n|]+)", text, re.IGNORECASE)
    if m:
        raw = m.group(1)
        # Strip anything after Warranty keyword
        warranty_idx = raw.upper().find("WARRANTY")
        if warranty_idx > 0:
            raw = raw[:warranty_idx]
        refs = [r.strip() for r in re.split(r"[,;]", raw)]
        data["oem_refs"] = [{"oem_number": sanitize_unicode_text(r), "reference_type": "OEM"}
                           for r in refs if r and _is_valid_oem_ref(r)]

    # Warranty
    m = re.search(r"Warranty Information:?\s*([^\n|]+)", text, re.IGNORECASE)
    if m:
        data["warranty"] = sanitize_unicode_text(_clean(m.group(1)))

    # Specs — lines like "Mounting Hardware Included: No" or table rows
    spec_matches = re.findall(
        r"([A-Z][A-Za-z ]{3,40})\s*[:\|]\s*(Yes|No|[0-9][^\n\|]{0,30})",
        text, re.IGNORECASE,
    )
    _SPEC_BLOCKLIST = {"interchange numbers", "warranty information",
                       "alternate inventory numbers", "show all warranty information",
                       "information"}
    for key, val in spec_matches:
        key = _clean(key)
        val = _clean(val)
        if (key and val and len(key) < 60
                and key.lower() not in _SPEC_BLOCKLIST
                and "continue shopping" not in val.lower()):
            data["specs"][sanitize_unicode_text(key)] = sanitize_unicode_text(val)

    # Category — from page title "Motor Mount | RockAuto" or first heading
    m = re.search(r"^([A-Z][A-Za-z &/\-]{3,40})\s*\|?\s*RockAuto", text, re.MULTILINE)
    if m:
        data["category"] = sanitize_unicode_text(_clean(m.group(1)))
    else:
        # Try first short line that looks like a part type
        for line in text.splitlines()[:10]:
            line = line.strip()
            if 4 < len(line) < 50 and re.match(r"^[A-Z][A-Za-z &/\-]+$", line):
                data["category"] = sanitize_unicode_text(line)
                break

    # Features / description — bullet-like lines
    features = re.findall(r"[•\-\*]\s*(.{15,120})", text)
    data["features"] = [sanitize_unicode_text(_clean(f)) for f in features[:10]]

    # Description — first paragraph-like block
    lines = [l.strip() for l in text.splitlines() if len(l.strip()) > 40]
    if lines:
        data["description"] = sanitize_unicode_text(lines[0][:500])

    # Fitment — year-range make model patterns like "2011-2024 Buick Enclave"
    fitment_matches = re.findall(
        r"(\d{4})\s*-\s*(\d{4})\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+([A-Z][A-Za-z0-9 \-]+)",
        text
    )
    fitment_data = []
    seen = set()
    for yr_start, yr_end, make, model in fitment_matches:
        key = (yr_start, yr_end, make.strip(), model.strip())
        if key not in seen:
            seen.add(key)
            fitment_data.append({
                "year_start": int(yr_start),
                "year_end": int(yr_end),
                "make": sanitize_unicode_text(make.strip()),
                "model": sanitize_unicode_text(model.strip().rstrip('.')),
            })
    # Also catch single-year patterns like "2016 Chevrolet Cruze"
    single_yr_matches = re.findall(
        r"(?<!\d)(\d{4})\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+([A-Z][A-Za-z0-9 \-]+?)(?:\s*[,;|\n]|$)",
        text
    )
    for yr, make, model in single_yr_matches:
        key = (yr, yr, make.strip(), model.strip())
        if key not in seen:
            seen.add(key)
            fitment_data.append({
                "year_start": int(yr),
                "year_end": int(yr),
                "make": sanitize_unicode_text(make.strip()),
                "model": sanitize_unicode_text(model.strip().rstrip('.')),
            })
    data["fitment_data"] = fitment_data[:50]

    return sanitize_unicode_dict(data)


def scrape_rockauto(part_number: str, brand: str = "ANCHOR") -> dict:
    """
    Scrape RockAuto using local Chrome. Drop-in replacement for
    the Firecrawl-based scraper_rockauto.scrape_rockauto().

    Args:
        part_number: Part number to search (e.g. "3217" or "SKM3217")
        brand:       Brand to look for in results (e.g. "ANCHOR" or "SKP")

    Returns: same dict schema as scraper_rockauto.scrape_rockauto()
    """
    brand = sanitize_unicode_text(brand.upper().strip())
    result = {
        "part_number":  sanitize_unicode_text(part_number),
        "brand":        brand,
        "source":       "RockAuto-Local",
        "search_url":   f"https://www.rockauto.com/en/partsearch/?partnum={part_number}",
        "found":        False,
        "blocked":      False,
        "category":     None,
        "oem_refs":     [],
        "image_url":    None,
        "moreinfo_url": None,
        "price":        None,
        "core_charge":  None,
        "specs":        {},
        "description":  None,
        "features":     [],
        "warranty":     None,
        "images":       [],
        "is_popular":   False,
        "error":        None,
        "listings":     [],      # NEW: All listings found
        "fitment_data": [],      # NEW: Vehicle fitment from URL
        "notes":        [],      # NEW: Additional notes
    }

    global _call_count
    try:
        # Periodic browser restart to prevent session degradation
        # Testing shows async/sync conflicts occur around call 37
        _call_count += 1
        if _call_count > 1 and _call_count % RESTART_EVERY == 0:
            print(f"[Local] Scheduled restart after {_call_count} calls (preventing session degradation)...")
            close()

        page = _get_page()

        print(f"[Local] Searching for {part_number} (brand={brand})...")
        page_text = _scrape_search(page, part_number)

        if "__CAPTCHA__" in page_text:
            result["blocked"] = True
            result["error"] = "CAPTCHA not resolved in time"
            return sanitize_unicode_dict(result)

        if "__NAV_ERROR__" in page_text:
            result["error"] = sanitize_unicode_text(page_text)
            return sanitize_unicode_dict(result)

        if not page_text or len(page_text) < 100:
            result["error"] = "Empty or very short page response"
            return sanitize_unicode_dict(result)

        # CHANGE 1: Extract price and category using DOM selectors (before parsing methods)
        extracted_price = None
        extracted_core_charge = None
        extracted_category = None

        try:
            # Extract price using multiple fallback selectors for reliability
            # Try primary selector first (existing approach)
            price_elems = page.query_selector_all("span[id*='dprice'][id*='[v]']")
            if price_elems and price_elems[0].inner_text().strip():
                extracted_price = sanitize_unicode_text(price_elems[0].inner_text().strip())
            else:
                # Fallback to class-based selector (more reliable from DOM inspection)
                price_elems = page.query_selector_all("span.ra-formatted-amount.listing-price")
                if price_elems and price_elems[0].inner_text().strip():
                    extracted_price = sanitize_unicode_text(price_elems[0].inner_text().strip())

            # Extract core charge: span[id*="dcore"][id*="[v]"]
            core_elems = page.query_selector_all("span[id*='dcore'][id*='[v]']")
            if core_elems:
                extracted_core_charge = sanitize_unicode_text(core_elems[0].inner_text().strip())

            # Extract category from page title (retry up to 3 times)
            for retry in range(3):
                try:
                    title = page.title()
                    if " | RockAuto" in title:
                        category = title.split(" | RockAuto")[0].strip()
                        if not any(word in category.lower() for word in ["shopping", "continue", "cart"]):
                            extracted_category = sanitize_unicode_text(category)
                            break
                except Exception:
                    pass
                if retry < 2:  # Don't sleep after last attempt
                    time.sleep(1)
        except Exception as e:
            print(f"[Local] DOM extraction failed: {e}")

        extracted_data = {
            "price": extracted_price,
            "core_charge": extracted_core_charge,
            "category": extracted_category
        }

        # CHANGE 2 & 3: Get ALL listings, not just the first one
        all_listings = _parse_all_listings_html(page, brand, part_number, extracted_data)

        # Fallback to text parsing if DOM method found nothing
        if not all_listings:
            text_listing = _parse_listing(page_text, brand, part_number, extracted_data)
            if text_listing["found"]:
                all_listings = [text_listing]

        if not all_listings:
            result["error"] = f"Brand '{brand}' not found for part '{part_number}'"
            return sanitize_unicode_dict(result)

        # Use first listing for backward compatibility
        listing = all_listings[0]
        result["listings"] = all_listings  # Store ALL listings

        result.update({
            "found":        True,
            "category":     listing.get("category"),
            "oem_refs":     listing.get("oem_refs", []),
            "image_url":    listing.get("image_url"),
            "moreinfo_url": listing.get("moreinfo_url"),
            "price":        listing.get("price"),
            "core_charge":  listing.get("core_charge"),
            "is_popular":   listing.get("is_popular", False),
        })

        # Fetch moreinfo page for richer data (OEM refs, specs, description, category, image)
        if listing.get("moreinfo_url"):
            print(f"[Local] Fetching moreinfo for {brand} {part_number}...")
            moreinfo_text = _scrape_moreinfo(page, listing["moreinfo_url"])
            if moreinfo_text:
                info = _parse_moreinfo_text(moreinfo_text)
                result.update({
                    "specs":       info["specs"],
                    "description": info["description"],
                    "features":    info["features"],
                    "warranty":    info["warranty"],
                })
                if info["oem_refs"]:
                    # Merge OEM refs from moreinfo with existing ones
                    existing_oems = {ref.get("oem_number") for ref in result.get("oem_refs", []) if isinstance(ref, dict)}
                    for new_ref in info["oem_refs"]:
                        if isinstance(new_ref, dict) and new_ref.get("oem_number") not in existing_oems:
                            result["oem_refs"].append(new_ref)

                # Category from moreinfo page title (e.g. "Motor Mount | RockAuto")
                if (not result["category"] or result["category"] == "Continue Shopping") and info.get("category"):
                    result["category"] = info["category"]

                # Fitment from moreinfo text (replaces broken URL-based approach)
                if info.get("fitment_data"):
                    result["fitment_data"] = info["fitment_data"]

                # FALLBACK: Extract price from description if DOM extraction failed
                if not result.get("price") and result.get("description"):
                    import re
                    m = re.search(r'\$(\d+\.\d{2})', result.get("description", ""))
                    if m:
                        result["price"] = f"${m.group(1)}"

                # FALLBACK: Extract category from description using comprehensive mapping
                if not result.get("category") and result.get("description"):
                    desc = result.get("description", "").lower()
                    # Map common description phrases to categories (ordered most specific first)
                    category_map = [
                        ('door lock actuator motor', 'DOOR LOCK ACTUATOR MOTOR'),
                        ('door lock motor', 'DOOR LOCK ACTUATOR MOTOR'),
                        ('actuator motor', 'DOOR LOCK ACTUATOR MOTOR'),
                        ('door lock actuator', 'DOOR LOCK ACTUATOR'),
                        ('lock actuator', 'DOOR LOCK ACTUATOR'),
                        ('door lock', 'DOOR LOCK ACTUATOR'),
                        ('engine cooling fan', 'ENGINE COOLING FAN ASSEMBLY'),
                        ('cooling fan assembly', 'ENGINE COOLING FAN ASSEMBLY'),
                        ('radiator fan', 'ENGINE COOLING FAN ASSEMBLY'),
                        ('cooling fan', 'ENGINE COOLING FAN ASSEMBLY'),
                        ('fan assembly', 'ENGINE COOLING FAN ASSEMBLY'),
                        ('engine mount', 'ENGINE MOUNT'),
                        ('motor mount', 'ENGINE MOUNT'),
                        ('transmission mount', 'ENGINE MOUNT'),
                        ('engine oil pan', 'ENGINE OIL PAN'),
                        ('oil pan', 'ENGINE OIL PAN'),
                        ('valve cover', 'ENGINE VALVE COVER'),
                        ('rocker cover', 'ENGINE VALVE COVER'),
                        ('water pump', 'ENGINE WATER PUMP'),
                        ('coolant pump', 'ENGINE WATER PUMP'),
                        ('hvac blower motor', 'HVAC BLOWER MOTOR'),
                        ('heater blower motor', 'HVAC BLOWER MOTOR'),
                        ('blower motor', 'HVAC BLOWER MOTOR'),
                        ('steering knuckle', 'STEERING KNUCKLE'),
                        ('window regulator', 'WINDOW REGULATOR'),
                        ('regulator', 'WINDOW REGULATOR'),
                    ]
                    for keyword, category in category_map:
                        if keyword in desc:
                            result["category"] = category
                            break

            # CHANGE 5: Parse alternate OEM references from moreinfo page
            alternate_oems = _parse_alternate_oem_refs(page)
            if alternate_oems:
                existing_oems = {ref.get("oem_number") for ref in result.get("oem_refs", []) if isinstance(ref, dict)}
                for alt_ref in alternate_oems:
                    if alt_ref.get("oem_number") not in existing_oems:
                        result["oem_refs"].append(alt_ref)

            # CHANGE 6: Extract warranty and notes
            warranty_notes = _parse_warranty_notes(page)
            if warranty_notes["warranty"] and not result.get("warranty"):
                result["warranty"] = warranty_notes["warranty"]
            if warranty_notes["notes"]:
                result["notes"] = warranty_notes["notes"]

            # CHANGE 7: Extract ALL product images
            all_images = _get_all_product_images(page)
            if all_images:
                result["images"] = all_images
                # Set primary image as main image_url if not already set
                if not result.get("image_url"):
                    primary_img = next((img for img in all_images if img.get("is_primary")), None)
                    if primary_img:
                        result["image_url"] = primary_img["url"]

            # Fallback to single image extraction if multiple images failed
            if not result.get("image_url"):
                img_url = _get_moreinfo_image_url(page)
                if img_url:
                    result["image_url"] = img_url

        print(f"[Local] Done. Found: {result['found']}, Category: {result['category']}, "
              f"OEMs: {len(result.get('oem_refs', []))}, Listings: {len(result['listings'])}")

        return sanitize_unicode_dict(result)

    except Exception as e:
        result["error"] = sanitize_unicode_text(str(e))
        print(f"[Local] Error: {e}")
        return sanitize_unicode_dict(result)


def close():
    """Close the browser and stop Playwright. Call when completely done processing."""
    global _pw, _context, _page
    try:
        if _context:
            _context.close()
    except Exception:
        pass
    try:
        if _pw:
            _pw.stop()   # CRITICAL: stops the asyncio event loop so a new one can start
    except Exception:
        pass
    _pw = None
    _context = None
    _page = None


def restart_browser():
    """Close and reopen the browser. Use after errors to get a clean session."""
    print("[Local] Restarting browser...")
    close()
    time.sleep(6)   # Allow asyncio event loop to fully stop before new playwright start
    _get_page()
    print("[Local] Browser restarted.")


if __name__ == "__main__":
    print("=" * 60)
    print("RockAuto Local Scraper Test")
    print("A Chrome window will open — this is normal.")
    print("=" * 60)

    try:
        print("\n--- Test 1: ANCHOR 3217 ---")
        r1 = scrape_rockauto("3217", brand="ANCHOR")
        print(json.dumps(r1, indent=2))

        time.sleep(3)

        print("\n--- Test 2: SKP SKM3217 ---")
        r2 = scrape_rockauto("SKM3217", brand="SKP")
        print(json.dumps(r2, indent=2))

    finally:
        input("\nPress Enter to close browser...")
        close()