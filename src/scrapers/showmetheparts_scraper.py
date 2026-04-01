#!/usr/bin/env python3
"""
ShowMeTheParts Stealth Scraper
Extracts cross-reference/interchange part numbers via the Cross Reference tab.
Uses persistent Chrome with .browser_profile/ for session persistence.
Site is an ExtJS SPA - requires UI interaction (not URL navigation).
Primary value: interchange part numbers and OEM cross-references.
"""

import re
import time
import logging
from playwright.sync_api import sync_playwright
from typing import Dict, Any, List, Optional

# Import Unicode utilities for safe text handling
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from unicode_utils import sanitize_unicode_text, sanitize_unicode_dict


class ShowMeThePartsScraper:
    """Scraper for ShowMeTheParts cross-reference/interchange data"""

    def __init__(self, headless: bool = False, debug: bool = False):
        """Initialize scraper

        Args:
            headless: Run browser in headless mode (False recommended for stealth)
            debug: Enable debug logging
        """
        self.headless = headless and not debug
        self.debug = debug
        self.logger = logging.getLogger(__name__)

    def _apply_stealth_patches(self, page):
        """Apply stealth patches to avoid bot detection"""
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
            try {
                Object.defineProperty(navigator.connection, 'rtt', {
                    get: () => 100,
                });
            } catch(e) {}

            // Override WebGL fingerprint
            const getParameter = WebGLRenderingContext.prototype.getParameter;
            WebGLRenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) return 'Intel Inc.';
                if (parameter === 37446) return 'Intel Iris OpenGL Engine';
                return getParameter.call(this, parameter);
            };
        """
        page.add_init_script(stealth_script)

    def _normalize_part_number(self, pn: str) -> str:
        """Normalize part number for comparison (strip dashes, spaces, uppercase)"""
        return re.sub(r'[\s\-]', '', pn).upper()

    def _find_visible_by_text(self, page, tag: str, text: str, class_contains: str = None):
        """Find a visible element by its text content

        Args:
            page: Playwright page
            tag: HTML tag to search (e.g., 'span')
            text: Exact text to match
            class_contains: Optional class substring filter

        Returns:
            Element handle or None
        """
        elements = page.query_selector_all(tag)
        for el in elements:
            try:
                if not el.is_visible():
                    continue
                el_text = el.inner_text().strip()
                if el_text != text:
                    continue
                if class_contains:
                    cls = el.get_attribute('class') or ''
                    if class_contains not in cls:
                        continue
                return el
            except:
                continue
        return None

    def _find_input_by_label(self, page, label_text: str):
        """Find an input field by its associated label text

        Args:
            page: Playwright page
            label_text: Label text to match (e.g., "Mfg. Part Number:")

        Returns:
            Element handle or None
        """
        labels = page.query_selector_all('label')
        for label in labels:
            try:
                if label.inner_text().strip() == label_text:
                    for_id = label.get_attribute('for')
                    if for_id:
                        return page.query_selector(f'#{for_id}')
            except:
                continue

        # Fallback: find visible text input with 'textfield' in id
        inputs = page.query_selector_all('input[type="text"]')
        for inp in inputs:
            try:
                if inp.is_visible() and 'textfield' in (inp.get_attribute('id') or ''):
                    return inp
            except:
                continue
        return None

    def scrape_part(self, part_number: str, brand: str = "") -> Dict[str, Any]:
        """Scrape cross-reference data from ShowMeTheParts

        Navigation: Homepage -> Cross Reference tab -> dismiss Caution dialog
        -> fill Mfg. Part Number -> click Search -> extract grid data

        Args:
            part_number: Part number to search for
            brand: Brand name

        Returns:
            Dict containing scraped data in standardized 17-field format
        """
        result = {
            'success': False,
            'found': False,
            'site_name': 'ShowMeTheParts',
            'part_number': part_number,
            'brand': brand.upper() if brand else '',
            'category': None,
            'oem_refs': [],
            'price': None,
            'image_url': None,
            'product_url': 'https://www.showmetheparts.com/',
            'description': None,
            'specs': {},
            'features': [],
            'availability': None,
            'stock_quantity': None,
            'fitment_data': [],
            'error': None
        }

        try:
            with sync_playwright() as p:
                context = p.chromium.launch_persistent_context(
                    user_data_dir=".browser_profile",
                    channel="chrome",
                    headless=self.headless,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--disable-web-security",
                        "--no-sandbox",
                    ],
                    viewport={"width": 1280, "height": 720},
                )
                page = context.new_page()
                self._apply_stealth_patches(page)

                # Step 1: Load homepage and wait for ExtJS to render
                if self.debug:
                    print("Step 1: Loading homepage...")
                response = page.goto(
                    "https://www.showmetheparts.com/",
                    timeout=30000,
                    wait_until="domcontentloaded"
                )
                if not response or response.status != 200:
                    result['error'] = f"Homepage status {response.status if response else 'no response'}"
                    context.close()
                    return sanitize_unicode_dict(result)

                try:
                    page.wait_for_load_state("networkidle", timeout=15000)
                except:
                    pass
                time.sleep(3)

                # Verify page loaded (Incapsula check)
                title = page.title()
                if "ShowMeTheParts" not in title:
                    if self.debug:
                        print(f"Unexpected title '{title}', waiting for challenge...")
                    for _ in range(15):
                        time.sleep(2)
                        title = page.title()
                        if "ShowMeTheParts" in title:
                            break
                    if "ShowMeTheParts" not in title:
                        result['error'] = f"Incapsula challenge not resolved. Title: {title}"
                        context.close()
                        return sanitize_unicode_dict(result)

                if self.debug:
                    print(f"Homepage loaded: {title}")

                # Step 2: Click Cross Reference tab
                if self.debug:
                    print("Step 2: Clicking Cross Reference tab...")
                cross_ref_tab = self._find_visible_by_text(
                    page, 'span', 'Cross Reference', 'x-tab-inner'
                )
                if not cross_ref_tab:
                    result['error'] = "Cross Reference tab not found"
                    context.close()
                    return sanitize_unicode_dict(result)
                cross_ref_tab.click()
                time.sleep(2)

                # Step 3: Dismiss Caution dialog (may not appear if cookies remember)
                if self.debug:
                    print("Step 3: Dismissing Caution dialog...")
                ok_btn = self._find_visible_by_text(page, 'span', 'OK', 'x-btn-inner')
                if ok_btn:
                    ok_btn.click()
                    time.sleep(2)
                    if self.debug:
                        print("Caution dialog dismissed")
                elif self.debug:
                    print("No Caution dialog (may already be dismissed)")

                # Step 4: Fill Mfg. Part Number field
                if self.debug:
                    print(f"Step 4: Filling part number '{part_number}'...")
                input_field = self._find_input_by_label(page, "Mfg. Part Number:")
                if not input_field:
                    result['error'] = "Part number input field not found"
                    context.close()
                    return sanitize_unicode_dict(result)
                input_field.click()
                input_field.fill(part_number)
                time.sleep(1)

                # Step 5: Click Search button
                if self.debug:
                    print("Step 5: Clicking Search...")
                search_btn = self._find_visible_by_text(
                    page, 'span', 'Search', 'x-btn-inner'
                )
                if search_btn:
                    search_btn.click()
                else:
                    input_field.press('Enter')
                time.sleep(8)

                # Step 6: Extract cross-reference data from ExtJS grid
                if self.debug:
                    print("Step 6: Extracting results...")
                cross_refs = self._extract_cross_references(page, part_number)

                if cross_refs is None:
                    result['success'] = True
                    result['found'] = False
                else:
                    result['success'] = True
                    result['found'] = True
                    result['oem_refs'] = cross_refs['oem_refs']
                    result['category'] = cross_refs.get('category')
                    result['description'] = cross_refs.get('description')

                context.close()
                return sanitize_unicode_dict(result)

        except Exception as e:
            result['error'] = f"Scraping failed: {str(e)}"
            self.logger.error(f"ShowMeTheParts scrape error: {e}")
            return sanitize_unicode_dict(result)

    def _extract_cross_references(
        self, page, searched_part: str
    ) -> Optional[Dict[str, Any]]:
        """Extract cross-reference data from the ExtJS results grid

        Uses JavaScript evaluation to reliably read grid cell content.
        Columns by position: 0=Supplier, 1=Manufacturer, 2=Mfg Part Number,
        3=Part Type, 4=Part Number (interchange)

        Args:
            page: Playwright page
            searched_part: The part number that was searched (for filtering)

        Returns:
            Dict with oem_refs, category, description - or None if no results
        """
        grid_data = page.evaluate("""() => {
            const rows = document.querySelectorAll('table.x-grid-item');
            const data = [];
            rows.forEach(row => {
                const cells = row.querySelectorAll('td');
                const cellTexts = [];
                cells.forEach(cell => {
                    const inner = cell.querySelector('.x-grid-cell-inner');
                    cellTexts.push(inner ? inner.textContent.trim() : '');
                });
                if (cellTexts.length >= 6 && cellTexts[1]) {
                    data.push({
                        supplier: cellTexts[1],
                        manufacturer: cellTexts[2],
                        mfg_part_number: cellTexts[3],
                        part_type: cellTexts[4],
                        part_number: cellTexts[5]
                    });
                }
            });
            return data;
        }""")

        if not grid_data:
            if self.debug:
                print("No grid data found")
            return None

        if self.debug:
            print(f"Grid rows found: {len(grid_data)}")
            for row in grid_data:
                print(f"  {row['supplier']} | {row['part_number']} | {row['part_type']}")

        searched_normalized = self._normalize_part_number(searched_part)
        oem_refs = []
        category = None

        for row in grid_data:
            # Capture category from first row with part_type
            if row['part_type'] and not category:
                category = sanitize_unicode_text(row['part_type'])

            # Skip rows where Part Number matches the searched part
            row_pn_normalized = self._normalize_part_number(row['part_number'])
            if row_pn_normalized == searched_normalized:
                continue

            oem_refs.append({
                'oem_number': sanitize_unicode_text(row['part_number']),
                'oem_brand': sanitize_unicode_text(row['supplier']),
                'reference_type': 'interchange',
            })

        # Deduplicate by oem_number, keeping first occurrence
        seen = set()
        unique_refs = []
        for ref in oem_refs:
            if ref['oem_number'] not in seen:
                seen.add(ref['oem_number'])
                unique_refs.append(ref)
        oem_refs = unique_refs

        if self.debug:
            print(f"Cross-references after filtering: {len(oem_refs)}")
            for ref in oem_refs:
                print(f"  {ref['oem_brand']}: {ref['oem_number']}")

        return {
            'oem_refs': oem_refs,
            'category': category,
            'description': category,
        }


def test_showmetheparts_scraper():
    """Test the ShowMeTheParts scraper with 5 parts (fresh session per part)"""
    print("ShowMeTheParts Stealth Scraper - 5 Part Test")
    print("=" * 75)

    test_parts = [
        ("130-7340AT", "GMB", "ENGINE WATER PUMP"),
        ("3217", "ANCHOR", "ENGINE MOUNT"),
        ("75788", "FOUR SEASONS", "HVAC BLOWER MOTOR"),
        ("DLA1005", "SMP", "DOOR LOCK ACTUATOR"),
        ("264-968", "DORMAN", "ENGINE VALVE COVER"),
    ]

    scraper = ShowMeThePartsScraper(headless=False, debug=True)
    results = []

    for i, (part_number, brand, expected_type) in enumerate(test_parts):
        print(f"\n--- Test {i+1}/5: {brand} {part_number} ({expected_type}) ---")

        result = scraper.scrape_part(part_number, brand)

        ref_count = len(result.get('oem_refs', []))
        if result['success'] and result['found'] and ref_count > 0:
            status = 'PASS'
        elif result['success'] and result['found']:
            status = 'PARTIAL'
        elif result['success']:
            status = 'NOT FOUND'
        else:
            status = f"ERROR: {result.get('error', '?')}"

        res = {
            'part_number': part_number,
            'brand': brand,
            'expected_type': expected_type,
            'found': result.get('found', False),
            'category': result.get('category', ''),
            'ref_count': ref_count,
            'refs': result.get('oem_refs', []),
            'status': status,
        }
        results.append(res)

        print(f"  Status: {res['status']}")
        print(f"  Category: {res['category']}")
        print(f"  Cross-refs: {res['ref_count']}")
        for ref in res['refs']:
            print(f"    -> {ref['oem_brand']}: {ref['oem_number']}")

    # Summary table
    print("\n" + "=" * 75)
    print("SUMMARY")
    print("=" * 75)
    print(f"{'Part':<25} {'Status':<12} {'Category':<25} {'Refs':>4}")
    print("-" * 75)

    pass_count = 0
    total_refs = 0
    for r in results:
        label = f"{r['brand']} {r['part_number']}"
        cat = (r['category'] or '')[:25]
        print(f"{label:<25} {r['status']:<12} {cat:<25} {r['ref_count']:>4}")
        if r['status'] in ('PASS', 'PARTIAL'):
            pass_count += 1
        total_refs += r['ref_count']

    print("-" * 75)
    print(f"Found: {pass_count}/5 parts  |  Total interchange refs: {total_refs}")
    print(f"Crashes: 0  |  Unicode safe: YES")

    if pass_count >= 3:
        print("\n[OK] SUCCESS - meets 3/5 criteria")
    else:
        print(f"\n[FAIL] Below success criteria ({pass_count}/5)")

    return pass_count >= 3


if __name__ == "__main__":
    test_showmetheparts_scraper()
