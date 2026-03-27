"""
Truly headless version of the scraper for background processing.
Uses headless Chrome with stealth patches - completely invisible.
"""

import re
import json
import time
import subprocess
import tempfile
import sys
from pathlib import Path

# Same interface as other scrapers
def scrape_rockauto_subprocess(part_number: str, brand: str) -> dict:
    """
    Headless subprocess scraper - completely invisible to user.
    Returns same format as other scrapers.
    """

    script_content = f'''
import asyncio
import sys
from pathlib import Path

# Add src to path
_src = Path(__file__).parent
sys.path.insert(0, str(_src))

async def main():
    from playwright.async_api import async_playwright
    try:
        from playwright_stealth import stealth_async
        _has_stealth = True
    except ImportError:
        _has_stealth = False

    result = {{"found": False, "error": None, "image_url": None}}

    try:
        async with async_playwright() as p:
            # HEADLESS Chrome - completely invisible
            browser = await p.chromium.launch(
                channel="chrome",
                headless=True,  # TRUE HEADLESS
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-infobars",
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-extensions",
                    "--disable-plugins",
                ]
            )

            context = await browser.new_context(
                viewport={{"width": 1280, "height": 720}},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )

            page = await context.new_page()

            if _has_stealth:
                await stealth_async(page)

            # Navigate and search
            await page.goto("https://www.rockauto.com/en/partsearch/", timeout=30000)

            # Fill search form
            await page.fill("#partnum_partsearch_007", "{part_number}")

            # Submit and wait for results
            await page.click("input[type=submit]")
            await page.wait_for_timeout(7000)

            # Look for product links
            links = await page.query_selector_all("a[href*='moreinfo.php']")

            for link in links:
                href = await link.get_attribute("href")
                if not href:
                    continue

                # Find parent container with part info
                parent = await link.evaluate_handle("el => el.closest('tr, div, td')")
                if not parent:
                    continue

                parent_text = await parent.text_content()
                if not parent_text:
                    continue

                # Check if this is the right brand
                if "{brand}".upper() in parent_text.upper():
                    # Found the right part, get image from moreinfo page
                    moreinfo_url = f"https://www.rockauto.com{{href}}"

                    await page.goto(moreinfo_url, timeout=30000)
                    await page.wait_for_timeout(2000)

                    # Look for product image
                    img_elements = await page.query_selector_all("img[src*='/info/']")
                    for img in img_elements:
                        src = await img.get_attribute("src")
                        if src and "/info/" in src:
                            if src.startswith("/"):
                                src = f"https://www.rockauto.com{{src}}"
                            result["image_url"] = src
                            result["found"] = True
                            break

                    if result["found"]:
                        break

            await browser.close()

    except Exception as e:
        result["error"] = str(e)

    print(json.dumps(result))

if __name__ == "__main__":
    asyncio.run(main())
'''

    # Write script to temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(script_content)
        temp_script = f.name

    try:
        # Run in subprocess with timeout
        result = subprocess.run([
            sys.executable, temp_script
        ], capture_output=True, text=True, timeout=45, cwd=Path(__file__).parent)

        if result.returncode == 0:
            try:
                return json.loads(result.stdout.strip())
            except json.JSONDecodeError:
                return {"found": False, "error": f"Invalid JSON output: {{result.stdout}}"}
        else:
            return {"found": False, "error": f"Script error: {{result.stderr}}"}

    except subprocess.TimeoutExpired:
        return {"found": False, "error": "Scraping timeout (45s)"}
    except Exception as e:
        return {"found": False, "error": str(e)}
    finally:
        # Clean up temp file
        try:
            Path(temp_script).unlink()
        except:
            pass