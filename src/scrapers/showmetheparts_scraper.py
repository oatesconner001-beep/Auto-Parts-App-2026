#!/usr/bin/env python3
"""
ShowMeTheParts Stealth Scraper
Bypasses Incapsula WAF using proper browser stealth techniques
"""

import time
import logging
from playwright.sync_api import sync_playwright
from typing import Dict, Any, Optional

class ShowMeThePartsScraper:
    """Stealth scraper for ShowMeTheParts with Incapsula bypass"""

    def __init__(self, headless: bool = True, debug: bool = False):
        """Initialize scraper with stealth configuration

        Args:
            headless: Run browser in headless mode
            debug: Enable debug logging and visible browser
        """
        self.headless = headless and not debug
        self.debug = debug
        self.logger = logging.getLogger(__name__)

        # Browser stealth configuration
        self.browser_args = [
            "--disable-blink-features=AutomationControlled",
            "--disable-web-security",
            "--no-sandbox",
            "--disable-features=TranslateUI",
            "--disable-dev-shm-usage",
            "--disable-extensions",
            "--no-first-run",
            "--disable-default-apps",
            "--disable-ipc-flooding-protection",
            "--window-position=-32000,-32000",  # Off-screen if headless fails
        ]

        self.context_options = {
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            "viewport": {"width": 1366, "height": 768},
            "extra_http_headers": {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
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
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
            }
        }

    def _apply_stealth_patches(self, page):
        """Apply comprehensive stealth patches to avoid detection"""
        stealth_script = """
            // Remove webdriver property
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });

            // Mock plugins
            Object.defineProperty(navigator, 'plugins', {
                get: () => [
                    {name: 'Chrome PDF Plugin', length: 1},
                    {name: 'Chrome PDF Viewer', length: 1},
                    {name: 'Native Client', length: 1}
                ],
            });

            // Mock languages
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en'],
            });

            // Override permissions query
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: 'default' }) :
                    originalQuery(parameters)
            );

            // Mock chrome runtime
            window.chrome = {
                runtime: {}
            };

            // Mock connection rtt
            Object.defineProperty(navigator.connection, 'rtt', {
                get: () => 50,
            });

            // Override toString to hide modifications
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) return 'Intel Inc.';
                if (parameter === 37446) return 'Intel Iris OpenGL Engine';
                return getParameter.call(this, parameter);
            };
        """

        page.add_init_script(stealth_script)

    def _wait_for_incapsula_challenge(self, page, timeout: int = 45) -> bool:
        """Wait for Incapsula challenge to complete

        Args:
            page: Playwright page object
            timeout: Maximum wait time in seconds

        Returns:
            bool: True if challenge completed successfully
        """
        if self.debug:
            print("Waiting for Incapsula challenge completion...")

        start_time = time.time()
        last_status = ""

        while time.time() - start_time < timeout:
            try:
                # Wait for page to stabilize
                page.wait_for_load_state("networkidle", timeout=5000)

                current_url = page.url
                title = page.title()

                # Get page content to analyze
                try:
                    body_text = page.inner_text("body", timeout=2000)
                except:
                    body_text = ""

                # Check multiple indicators of successful challenge completion
                success_indicators = [
                    # Title indicates real page
                    title and ("ShowMeTheParts" in title or "Parts" in title),
                    # Body has substantial content
                    len(body_text) > 200,
                    # No challenge indicators in body
                    "Incapsula incident ID" not in body_text,
                    # No challenge iframe present
                    not page.query_selector("iframe[src*='Incapsula_Resource']"),
                    # Has navigation or search elements
                    page.query_selector("nav, .search, input[type='search'], #search") is not None
                ]

                success_count = sum(1 for indicator in success_indicators if indicator)

                status = f"URL: {current_url[:50]}... | Title: {title} | Content: {len(body_text)} chars | Indicators: {success_count}/5"

                if status != last_status:
                    if self.debug:
                        print(f"Challenge status: {status}")
                    last_status = status

                # Challenge completed if we have multiple positive indicators
                if success_count >= 3:
                    if self.debug:
                        print(f"Challenge completed! {success_count}/5 success indicators met")
                    return True

                # Also check for direct HTTP 200 response to a simple request
                try:
                    # Try to navigate to the same page again to test if challenge is resolved
                    test_response = page.evaluate("""() => {
                        return fetch(window.location.href, {
                            method: 'GET',
                            credentials: 'same-origin'
                        }).then(response => response.status);
                    }""")

                    if test_response == 200:
                        if self.debug:
                            print("Challenge completed - fetch test returned 200")
                        return True

                except Exception as e:
                    if self.debug:
                        print(f"Fetch test failed: {e}")

                # Shorter wait intervals for more responsive checking
                time.sleep(2)

            except Exception as e:
                if self.debug:
                    print(f"Challenge wait error: {e}")
                time.sleep(2)

        if self.debug:
            print(f"Challenge wait timeout after {timeout}s - may not have completed")
        return False

    def scrape_part(self, part_number: str, brand: str = "anchor") -> Dict[str, Any]:
        """Scrape part information from ShowMeTheParts

        Args:
            part_number: Part number to search for
            brand: Brand name (default: anchor)

        Returns:
            Dict containing scraped data in standardized format
        """
        result = {
            'success': False,
            'found': False,
            'site_name': 'ShowMeTheParts',
            'part_number': part_number,
            'brand': brand.upper(),
            'category': None,
            'oem_refs': [],
            'price': None,
            'image_url': None,
            'product_url': None,
            'description': None,
            'specs': {},
            'features': [],
            'availability': None,
            'stock_quantity': None,
            'error': None
        }

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=self.headless,
                    args=self.browser_args
                )

                context = browser.new_context(**self.context_options)
                page = context.new_page()

                # Apply stealth patches
                self._apply_stealth_patches(page)

                # Step 1: Session warmup - visit homepage
                if self.debug:
                    print("Step 1: Visiting homepage for session establishment...")

                homepage_response = page.goto("https://www.showmetheparts.com/",
                                            timeout=30000, wait_until="domcontentloaded")

                homepage_status = homepage_response.status if homepage_response else "no response"
                if self.debug:
                    print(f"Homepage initial response: {homepage_status}")

                # Always wait for challenge regardless of status - some challenges return 200 initially
                challenge_passed = self._wait_for_incapsula_challenge(page)

                if not challenge_passed:
                    # Try one more time with longer wait
                    if self.debug:
                        print("First challenge attempt failed, trying extended wait...")
                    time.sleep(10)
                    challenge_passed = self._wait_for_incapsula_challenge(page, timeout=60)

                    if not challenge_passed:
                        result['error'] = "Failed to pass Incapsula challenge after extended attempts"
                        if self.debug:
                            current_url = page.url
                            page_content = page.content()[:500]
                            print(f"Final URL: {current_url}")
                            print(f"Final content: {page_content}")
                        return result

                # Additional wait for session establishment
                if self.debug:
                    print("Challenge passed, establishing session...")
                time.sleep(3)

                # Step 2: Visit brand page
                if self.debug:
                    print(f"Step 2: Visiting {brand} brand page...")

                brand_url = f"https://www.showmetheparts.com/{brand.lower()}/"
                brand_response = page.goto(brand_url, timeout=30000, wait_until="domcontentloaded")

                if brand_response and brand_response.status != 200:
                    result['error'] = f"Failed to access brand page: {brand_response.status}"
                    return result

                time.sleep(2)

                # Step 3: Perform search
                if self.debug:
                    print(f"Step 3: Searching for part {part_number}...")

                search_url = f"https://www.showmetheparts.com/{brand.lower()}/search?searchterm={part_number}"
                result['product_url'] = search_url

                search_response = page.goto(search_url, timeout=30000, wait_until="domcontentloaded")

                if not search_response or search_response.status != 200:
                    result['error'] = f"Search failed with status: {search_response.status if search_response else 'no response'}"
                    return result

                # Wait for search results to load
                time.sleep(3)

                # Step 4: Extract data
                page_title = page.title()
                body_text = page.inner_text("body")

                if self.debug:
                    print(f"Page title: {page_title}")
                    print(f"Body text preview: {body_text[:500]}")

                # Check for "no results" indicators
                if any(phrase in body_text.lower() for phrase in ["no result", "not found", "0 result", "no parts found"]):
                    result['success'] = True
                    result['found'] = False
                    result['error'] = "Part not found on site"
                else:
                    result['success'] = True
                    result['found'] = True

                    # Extract part information using various selectors
                    part_info = self._extract_part_info(page)
                    result.update(part_info)

                browser.close()
                return result

        except Exception as e:
            result['error'] = f"Scraping failed: {str(e)}"
            if self.debug:
                import traceback
                traceback.print_exc()
            return result

    def _extract_part_info(self, page) -> Dict[str, Any]:
        """Extract part information from the search results page

        Args:
            page: Playwright page object

        Returns:
            Dict containing extracted information
        """
        info = {}

        try:
            # Try various selectors for part name/title
            title_selectors = [
                "h1", ".part-name", ".product-name", ".part-title",
                "[class*='part-name']", "[class*='product-title']",
                ".search-result-title", ".result-title"
            ]

            for selector in title_selectors:
                elements = page.query_selector_all(selector)
                if elements:
                    texts = [el.inner_text().strip() for el in elements if el.inner_text().strip()]
                    if texts:
                        info['description'] = texts[0]
                        break

            # Extract category information
            category_selectors = [".category", ".part-category", "[class*='category']"]
            for selector in category_selectors:
                elements = page.query_selector_all(selector)
                if elements:
                    category_text = elements[0].inner_text().strip()
                    if category_text:
                        info['category'] = category_text
                        break

            # Extract price
            price_selectors = [".price", ".part-price", "[class*='price']", ".cost"]
            for selector in price_selectors:
                elements = page.query_selector_all(selector)
                if elements:
                    price_text = elements[0].inner_text().strip()
                    if "$" in price_text:
                        info['price'] = price_text
                        break

            # Extract images
            images = page.query_selector_all("img")
            for img in images:
                src = img.get_attribute("src")
                alt = img.get_attribute("alt")
                if src and any(keyword in src.lower() for keyword in ["part", "product"]):
                    if src.startswith("//"):
                        src = "https:" + src
                    elif src.startswith("/"):
                        src = "https://www.showmetheparts.com" + src
                    info['image_url'] = src
                    break

            # Extract OEM references from tables or lists
            oem_refs = []
            table_elements = page.query_selector_all("table, .oem, .reference, [class*='oem'], [class*='reference']")
            for element in table_elements:
                text = element.inner_text().lower()
                if "oem" in text or "reference" in text:
                    # Extract potential OEM numbers (alphanumeric patterns)
                    import re
                    oem_patterns = re.findall(r'\b[A-Z0-9]{5,20}\b', element.inner_text().upper())
                    oem_refs.extend(oem_patterns[:5])  # Limit to 5 references

            if oem_refs:
                info['oem_refs'] = list(set(oem_refs))  # Remove duplicates

        except Exception as e:
            if self.debug:
                print(f"Error extracting part info: {e}")

        return info

def test_showmetheparts_scraper():
    """Test the ShowMeTheParts scraper"""
    print("Testing ShowMeTheParts Stealth Scraper")
    print("=" * 50)

    # Test with debug mode enabled
    scraper = ShowMeThePartsScraper(headless=False, debug=True)

    # Test with known part
    result = scraper.scrape_part("3217", "anchor")

    print("\nScraping Results:")
    print("-" * 30)
    for key, value in result.items():
        print(f"{key}: {value}")

    if result['success']:
        print(f"\n[SUCCESS] ShowMeTheParts scraper working!")
        print(f"Found: {result['found']}")
        if result['found']:
            print(f"Category: {result.get('category', 'N/A')}")
            print(f"Price: {result.get('price', 'N/A')}")
            print(f"OEM Refs: {len(result.get('oem_refs', []))}")
    else:
        print(f"\n[FAILED] {result.get('error', 'Unknown error')}")

    return result['success']

if __name__ == "__main__":
    test_showmetheparts_scraper()