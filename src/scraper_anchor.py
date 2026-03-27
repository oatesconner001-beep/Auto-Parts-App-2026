"""
ShowMeTheParts Anchor brand scraper.
Scrapes part info for a given Anchor part number.
"""

import asyncio
import json
from playwright.async_api import async_playwright


SEARCH_URL = "https://www.showmetheparts.com/anchor/search?searchterm={part_number}"
PART_URL   = "https://www.showmetheparts.com/anchor/{part_number}"


async def scrape_anchor(part_number: str, headless: bool = True) -> dict:
    """
    Scrape ShowMeTheParts for an Anchor part number.
    Returns a dict with all found data, or error info if blocked/not found.
    """
    result = {
        "part_number": part_number,
        "source": "ShowMeTheParts/Anchor",
        "url_searched": SEARCH_URL.format(part_number=part_number),
        "found": False,
        "blocked": False,
        "part_name": None,
        "description": None,
        "fitment": [],
        "specs": {},
        "images": [],
        "raw_text": None,
        "error": None,
    }

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-web-security",
                "--no-sandbox",
            ],
        )
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
            extra_http_headers={
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Upgrade-Insecure-Requests": "1",
            },
        )
        page = await context.new_page()
        # Override the navigator.webdriver flag so it's not detectable
        await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        try:
            # Step 1: Visit homepage first to establish cookies/session
            print("[Anchor] Step 1: Visiting homepage to establish session...")
            home_resp = await page.goto("https://www.showmetheparts.com/anchor/", wait_until="domcontentloaded", timeout=30000)
            home_status = home_resp.status if home_resp else "no response"
            print(f"[Anchor] Homepage status: {home_status}")
            await asyncio.sleep(2)

            # Step 2: Now navigate to the search
            url = SEARCH_URL.format(part_number=part_number)
            print(f"[Anchor] Step 2: Navigating to search: {url}")
            response = await page.goto(url, wait_until="domcontentloaded", timeout=30000)

            status = response.status if response else "no response"
            print(f"[Anchor] Search HTTP status: {status}")

            if status == 403:
                result["blocked"] = True
                result["error"] = "HTTP 403 — site blocked the request even with browser UA"
                return result

            # Wait a moment for JS to render
            await asyncio.sleep(2)

            # Grab the full page title
            page_title = await page.title()
            print(f"[Anchor] Page title: {page_title}")

            # Check for Cloudflare or access denied
            body_text = await page.inner_text("body")
            if "cloudflare" in body_text.lower() or "access denied" in body_text.lower() or "verify you are human" in body_text.lower():
                result["blocked"] = True
                result["error"] = "Bot/Cloudflare challenge detected"
                result["raw_text"] = body_text[:500]
                return result

            # ---- Try to find search results ----
            # Dump the full page text so we can see what's there
            result["raw_text"] = body_text[:5000]

            # Look for the part name / title (common patterns on SMTP)
            selectors_to_try = [
                "h1",
                ".part-name",
                ".product-name",
                ".part-title",
                "[class*='part-name']",
                "[class*='product-title']",
                ".search-result-title",
                ".result-title",
            ]
            for sel in selectors_to_try:
                try:
                    els = await page.query_selector_all(sel)
                    if els:
                        texts = [await el.inner_text() for el in els]
                        print(f"[Anchor] Selector '{sel}': {texts}")
                except Exception:
                    pass

            # Look for description
            desc_selectors = [
                ".part-description",
                ".description",
                "[class*='description']",
                "p",
            ]
            for sel in desc_selectors[:2]:
                try:
                    els = await page.query_selector_all(sel)
                    if els:
                        texts = [await el.inner_text() for el in els[:3]]
                        print(f"[Anchor] Desc selector '{sel}': {texts}")
                except Exception:
                    pass

            # Look for fitment / applications table
            table_selectors = [
                "table",
                ".fitment",
                ".application",
                "[class*='fitment']",
                "[class*='application']",
                "[class*='vehicle']",
            ]
            for sel in table_selectors:
                try:
                    els = await page.query_selector_all(sel)
                    if els:
                        text = await els[0].inner_text()
                        print(f"[Anchor] Table/fitment '{sel}': {text[:300]}")
                except Exception:
                    pass

            # Collect all image src attributes
            images = await page.query_selector_all("img")
            img_srcs = []
            for img in images:
                src = await img.get_attribute("src")
                alt = await img.get_attribute("alt")
                if src and ("part" in src.lower() or "product" in src.lower() or part_number.lower() in src.lower()):
                    img_srcs.append({"src": src, "alt": alt})
            result["images"] = img_srcs[:5]

            # Check if "no results" message appears
            if "no result" in body_text.lower() or "not found" in body_text.lower() or "0 result" in body_text.lower():
                result["found"] = False
                result["error"] = "Part not found on site"
            else:
                result["found"] = True

            # Also try navigating directly to the part URL
            direct_url = PART_URL.format(part_number=part_number)
            print(f"\n[Anchor] Also trying direct URL: {direct_url}")
            await asyncio.sleep(1)
            resp2 = await page.goto(direct_url, wait_until="domcontentloaded", timeout=30000)
            status2 = resp2.status if resp2 else "no response"
            print(f"[Anchor] Direct URL HTTP status: {status2}")

            if status2 == 200:
                await asyncio.sleep(2)
                direct_text = await page.inner_text("body")
                print(f"[Anchor] Direct URL page text (first 2000 chars):\n{direct_text[:2000]}")
                result["direct_url"] = direct_url
                result["direct_url_text"] = direct_text[:3000]

                # Re-check selectors on direct page
                print("\n[Anchor] Checking selectors on direct URL page:")
                for sel in selectors_to_try:
                    try:
                        els = await page.query_selector_all(sel)
                        if els:
                            texts = [await el.inner_text() for el in els[:3]]
                            if any(t.strip() for t in texts):
                                print(f"  '{sel}': {texts}")
                    except Exception:
                        pass

        except Exception as e:
            result["error"] = str(e)
            print(f"[Anchor] Exception: {e}")

        finally:
            await browser.close()

    return result


async def main():
    part_number = "130-7340AT"
    print(f"=== Testing Anchor scraper with part: {part_number} ===\n")
    data = await scrape_anchor(part_number, headless=True)
    print("\n=== FINAL RESULT ===")
    print(json.dumps(data, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
