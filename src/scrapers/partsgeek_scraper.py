#!/usr/bin/env python3
"""
PartsGeek Scraper
Searches partsgeek.com for auto parts data including pricing, fitment, and OEM references.
Uses persistent Chrome with .browser_profile/ for session persistence.
No bot protection on site (Cloudflare analytics only).
"""

import re
import time
import logging
from typing import Dict, List, Any, Optional, Tuple
from playwright.sync_api import sync_playwright
from datetime import datetime

# Import Unicode utilities for safe text handling
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from unicode_utils import sanitize_unicode_text, sanitize_unicode_dict


class PartsGeekScraper:
    """Scraper for PartsGeek auto parts website"""

    def __init__(self, headless: bool = False):
        """Initialize PartsGeek scraper

        Args:
            headless: Whether to run browser in headless mode (False for persistent Chrome)
        """
        self.headless = headless
        self.logger = logging.getLogger(__name__)
        self.base_url = "https://www.partsgeek.com"
        self.search_url = "https://www.partsgeek.com/ss/?i=1&ssq={part_number}"

        # Category map — exact 28-keyword, 10-category list from scraper_local.py
        self.category_map = [
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

        # Brand alias map for sites that use full names instead of abbreviations
        self.brand_aliases = {
            'SMP': ['SMP', 'STANDARD MOTOR PRODUCTS', 'STANDARD MOTOR', 'STANDARD'],
            'FOUR SEASONS': ['FOUR SEASONS', '4 SEASONS', 'FOURSEASONS'],
            'GMB': ['GMB'],
            'ANCHOR': ['ANCHOR', 'ANCHOR INDUSTRIES'],
            'DORMAN': ['DORMAN', 'DORMAN PRODUCTS'],
        }

    def scrape_part(self, part_number: str, brand: str, config: Dict = None) -> Dict[str, Any]:
        """Scrape PartsGeek part data following standardized interface

        Args:
            part_number: Part number to search (e.g., "130-7340AT")
            brand: Brand name to filter by (e.g., "GMB")
            config: Site configuration (rate limits, etc.)

        Returns:
            Dict: Standardized scraping results (17 fields)
        """
        result = {
            'success': False,
            'found': False,
            'site_name': 'PartsGeek',
            'part_number': part_number,
            'brand': brand,
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
            'fitment_data': [],
            'error': None
        }

        try:
            with sync_playwright() as p:
                context, page = self._launch_browser(p)

                try:
                    # Navigate to search results
                    search_url = self.search_url.format(part_number=part_number)
                    result['product_url'] = search_url
                    print(f"[PartsGeek] Searching: {search_url}")

                    response = page.goto(search_url, timeout=30000)

                    if not response or response.status != 200:
                        status = response.status if response else "no response"
                        result['error'] = f"Search page failed: HTTP {status}"
                        return result

                    # Wait for product results to load
                    page.wait_for_timeout(3000)

                    # Check if any results exist
                    products = page.query_selector_all('.product')
                    if not products:
                        result['error'] = f"No search results for {part_number}"
                        result['success'] = True
                        return result

                    print(f"[PartsGeek] Found {len(products)} product results")

                    # Find the product matching our brand
                    matching_product = self._find_matching_product(page, products, brand)

                    if not matching_product:
                        result['error'] = f"No product matching brand '{brand}'"
                        result['success'] = True
                        return result

                    # Extract all fields from matching product
                    result['success'] = True
                    self._extract_description(matching_product, result)
                    self._extract_price(matching_product, result)
                    self._extract_category(result)
                    self._extract_brand_and_part(matching_product, result)
                    self._extract_stock(matching_product, result)
                    self._extract_image(matching_product, result)
                    self._extract_specs(matching_product, result)
                    self._extract_fitment(matching_product, result)

                    # Apply Unicode sanitization to all scraped data
                    result = self._sanitize_result_data(result)

                    # Determine if part was actually found
                    result['found'] = (
                        result['description'] is not None or
                        result['price'] is not None or
                        len(result['fitment_data']) > 0
                    )

                    if result['found']:
                        safe_desc = sanitize_unicode_text(result.get('description', 'N/A'))
                        print(f"[PartsGeek] Successfully scraped {brand} {part_number}")
                        print(f"          Title: {safe_desc[:60]}")
                        print(f"          Price: {result.get('price', 'N/A')}")
                        print(f"          Category: {result.get('category', 'N/A')}")
                        print(f"          Stock: {result.get('availability', 'N/A')}")
                        print(f"          Fitment Records: {len(result.get('fitment_data', []))}")
                    else:
                        result['error'] = "Product found but no data extracted"

                except Exception as e:
                    result['error'] = f"Scraping error: {str(e)}"
                    self.logger.error(f"PartsGeek scraping error for {part_number}: {e}")

                finally:
                    context.close()

        except Exception as e:
            result['error'] = f"Browser error: {str(e)}"
            self.logger.error(f"PartsGeek browser error: {e}")

        return result

    def _launch_browser(self, p) -> Tuple:
        """Launch persistent Chrome browser with .browser_profile/

        Args:
            p: Playwright instance

        Returns:
            Tuple: (context, page)
        """
        context = p.chromium.launch_persistent_context(
            user_data_dir=".browser_profile",
            channel="chrome",
            headless=self.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-web-security",
                "--no-sandbox"
            ],
            viewport={"width": 1280, "height": 720}
        )
        page = context.new_page()
        return context, page

    def _find_matching_product(self, page, products, brand: str):
        """Find the product element matching the target brand

        Args:
            page: Playwright page
            products: List of .product element handles
            brand: Target brand to match (e.g., "GMB", "ANCHOR")

        Returns:
            ElementHandle or None
        """
        brand_upper = brand.strip().upper()
        found_brands = []

        for product in products:
            try:
                # Extract brand from .product-attribute-heading siblings
                headings = product.query_selector_all('.product-attribute-heading')
                for heading in headings:
                    heading_text = heading.inner_text().strip()
                    if 'brand' in heading_text.lower():
                        # Brand value is in the next sibling or adjacent text
                        parent = heading.evaluate_handle('el => el.parentElement')
                        parent_text = parent.inner_text().strip() if parent else ""
                        # Extract value after the heading text
                        brand_value = parent_text.replace(heading_text, '').strip().strip(':').strip()

                        if not brand_value:
                            # Try next sibling element
                            sibling = heading.evaluate_handle('el => el.nextElementSibling')
                            if sibling:
                                brand_value = sibling.inner_text().strip()

                        if brand_value:
                            found_brands.append(brand_value)
                            brand_value_upper = brand_value.upper()
                            # Exact match or substring match
                            if brand_upper == brand_value_upper or brand_upper in brand_value_upper:
                                print(f"[PartsGeek] Brand match: '{brand_value}' matches '{brand}'")
                                return product
                            # Alias match: check if site brand matches any known alias
                            aliases = self.brand_aliases.get(brand_upper, [])
                            for alias in aliases:
                                if alias == brand_value_upper or alias in brand_value_upper:
                                    print(f"[PartsGeek] Brand match (alias): '{brand_value}' matches alias '{alias}' for '{brand}'")
                                    return product

                # Fallback: check full product text for brand name
                product_text = product.inner_text().upper()
                if brand_upper in product_text:
                    print(f"[PartsGeek] Brand match (text fallback): found '{brand}' in product text")
                    return product

            except Exception as e:
                self.logger.error(f"Error checking product brand: {e}")
                continue

        if found_brands:
            safe_brands = [sanitize_unicode_text(b) for b in set(found_brands)]
            print(f"[PartsGeek] Brand '{brand}' not found. Available brands: {safe_brands}")
        else:
            print(f"[PartsGeek] Could not extract brand info from any product")

        return None

    def _extract_description(self, product, result: Dict) -> None:
        """Extract product title/description"""
        try:
            title_el = product.query_selector('.product-title')
            if title_el:
                result['description'] = title_el.inner_text().strip()
        except Exception as e:
            self.logger.error(f"Error extracting description: {e}")

    def _extract_price(self, product, result: Dict) -> None:
        """Extract product price"""
        try:
            price_el = product.query_selector('.product-price')
            if price_el:
                price_text = price_el.inner_text().strip()
                # Clean to $XX.XX format
                price_match = re.search(r'\$[\d,]+\.?\d*', price_text)
                if price_match:
                    result['price'] = price_match.group(0)
        except Exception as e:
            self.logger.error(f"Error extracting price: {e}")

    def _extract_category(self, result: Dict) -> None:
        """Map description to standard category using category_map"""
        try:
            desc = result.get('description', '')
            if not desc:
                return
            desc_lower = desc.lower()
            for keyword, category in self.category_map:
                if keyword in desc_lower:
                    result['category'] = category
                    return
        except Exception as e:
            self.logger.error(f"Error extracting category: {e}")

    def _extract_brand_and_part(self, product, result: Dict) -> None:
        """Extract brand name and part number from product attributes"""
        try:
            headings = product.query_selector_all('.product-attribute-heading')
            for heading in headings:
                heading_text = heading.inner_text().strip().lower()
                parent = heading.evaluate_handle('el => el.parentElement')
                parent_text = parent.inner_text().strip() if parent else ""
                # Get value after heading
                value = parent_text.replace(heading.inner_text().strip(), '').strip().strip(':').strip()

                if not value:
                    sibling = heading.evaluate_handle('el => el.nextElementSibling')
                    if sibling:
                        value = sibling.inner_text().strip()

                if 'brand' in heading_text and value:
                    result['brand'] = value
                elif 'part' in heading_text and '#' in heading_text and value:
                    result['part_number'] = value

        except Exception as e:
            self.logger.error(f"Error extracting brand/part: {e}")

    def _extract_stock(self, product, result: Dict) -> None:
        """Extract stock/availability information"""
        try:
            stock_el = product.query_selector('.product-stock')
            if stock_el:
                stock_text = stock_el.inner_text().strip()
                result['availability'] = stock_text

                # Parse quantity from "(63) In Stock" format
                qty_match = re.search(r'\((\d+)\)', stock_text)
                if qty_match:
                    result['stock_quantity'] = int(qty_match.group(1))

                # Normalize availability text
                if 'in stock' in stock_text.lower():
                    result['availability'] = 'In Stock'
                elif 'out of stock' in stock_text.lower():
                    result['availability'] = 'Out of Stock'
        except Exception as e:
            self.logger.error(f"Error extracting stock: {e}")

    def _extract_image(self, product, result: Dict) -> None:
        """Extract product image URL"""
        try:
            img_el = product.query_selector('.product-image img[data-image]')
            if img_el:
                image_url = img_el.get_attribute('data-image')
                if image_url:
                    # Ensure full URL
                    if image_url.startswith('//'):
                        image_url = 'https:' + image_url
                    elif image_url.startswith('/'):
                        image_url = self.base_url + image_url
                    result['image_url'] = image_url
            else:
                # Fallback: any img in product-image
                img_el = product.query_selector('.product-image img')
                if img_el:
                    src = img_el.get_attribute('src')
                    if src:
                        if src.startswith('//'):
                            src = 'https:' + src
                        elif src.startswith('/'):
                            src = self.base_url + src
                        result['image_url'] = src
        except Exception as e:
            self.logger.error(f"Error extracting image: {e}")

    def _extract_specs(self, product, result: Dict) -> None:
        """Extract technical specifications from product attributes"""
        try:
            headings = product.query_selector_all('.product-attribute-heading')
            skip_keys = {'brand', 'part #', 'part#', 'part number'}

            for heading in headings:
                heading_text = heading.inner_text().strip()
                if heading_text.lower().rstrip(':').strip() in skip_keys:
                    continue

                parent = heading.evaluate_handle('el => el.parentElement')
                parent_text = parent.inner_text().strip() if parent else ""
                value = parent_text.replace(heading_text, '').strip().strip(':').strip()

                if not value:
                    sibling = heading.evaluate_handle('el => el.nextElementSibling')
                    if sibling:
                        value = sibling.inner_text().strip()

                if value and len(value) < 200:
                    spec_name = heading_text.rstrip(':').strip()
                    result['specs'][spec_name] = value

        except Exception as e:
            self.logger.error(f"Error extracting specs: {e}")

    def _extract_fitment(self, product, result: Dict) -> None:
        """Extract fitment data as year_start/year_end ranges

        PartsGeek shows fitment as "2003-2006 Chevrolet Silverado 1500"
        Stored as year_start=2003, year_end=2006 matching fitment table schema.
        """
        try:
            fitment_rows = product.query_selector_all('.fitment-container table tbody tr')
            if not fitment_rows:
                return

            print(f"[PartsGeek] Found {len(fitment_rows)} fitment rows")

            for row in fitment_rows:
                try:
                    cells = row.query_selector_all('.application-content')
                    if not cells:
                        cells = row.query_selector_all('td')
                    if not cells:
                        continue

                    # First cell: year range + make + model
                    vehicle_text = cells[0].inner_text().strip() if cells else ""
                    if not vehicle_text:
                        continue

                    # Engine from second cell if available
                    engine = None
                    if len(cells) > 1:
                        engine_text = cells[1].inner_text().strip()
                        if engine_text:
                            engine = engine_text

                    # Parse year range: "2003-2006 Chevrolet Silverado 1500"
                    year_match = re.match(r'(\d{4})(?:\s*-\s*(\d{4}))?\s+(.+)', vehicle_text)
                    if not year_match:
                        continue

                    year_start = int(year_match.group(1))
                    year_end = int(year_match.group(2)) if year_match.group(2) else year_start

                    vehicle_part = year_match.group(3).strip()
                    # Split into make and model: first word is make, rest is model
                    vehicle_parts = vehicle_part.split(None, 1)
                    if not vehicle_parts:
                        continue

                    make = vehicle_parts[0]
                    model = vehicle_parts[1] if len(vehicle_parts) > 1 else ""

                    result['fitment_data'].append({
                        'year_start': year_start,
                        'year_end': year_end,
                        'make': make,
                        'model': model,
                        'engine': engine
                    })

                except Exception as e:
                    self.logger.error(f"Error parsing fitment row: {e}")
                    continue

            if result['fitment_data']:
                print(f"[PartsGeek] Parsed {len(result['fitment_data'])} fitment records")

        except Exception as e:
            self.logger.error(f"Error extracting fitment: {e}")

    def _sanitize_result_data(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Apply Unicode sanitization to all scraped data to prevent crashes"""
        try:
            sanitized_result = sanitize_unicode_dict(result)

            if 'description' in sanitized_result and sanitized_result['description']:
                sanitized_result['description'] = sanitize_unicode_text(sanitized_result['description'])

            if 'error' in sanitized_result and sanitized_result['error']:
                sanitized_result['error'] = sanitize_unicode_text(sanitized_result['error'])

            if 'oem_refs' in sanitized_result and isinstance(sanitized_result['oem_refs'], list):
                sanitized_result['oem_refs'] = [
                    sanitize_unicode_text(ref) for ref in sanitized_result['oem_refs']
                    if ref is not None
                ]

            if 'fitment_data' in sanitized_result and isinstance(sanitized_result['fitment_data'], list):
                sanitized_fitment = []
                for fitment in sanitized_result['fitment_data']:
                    if isinstance(fitment, dict):
                        clean_fitment = {
                            'year_start': fitment.get('year_start'),
                            'year_end': fitment.get('year_end'),
                            'make': sanitize_unicode_text(str(fitment.get('make', ''))),
                            'model': sanitize_unicode_text(str(fitment.get('model', ''))),
                            'engine': sanitize_unicode_text(str(fitment.get('engine', ''))) if fitment.get('engine') else None
                        }
                        sanitized_fitment.append(clean_fitment)
                sanitized_result['fitment_data'] = sanitized_fitment

            return sanitized_result

        except Exception as e:
            self.logger.error(f"Error sanitizing result data: {e}")
            return result


def test_partsgeek_scraper():
    """Test the PartsGeek scraper with 5 verified parts from Excel file"""
    print("TESTING PARTSGEEK SCRAPER")
    print("=" * 60)

    scraper = PartsGeekScraper(headless=False)

    test_parts = [
        ("130-7340AT", "GMB", "ENGINE WATER PUMP"),
        ("3217", "ANCHOR", "ENGINE MOUNT"),
        ("75788", "FOUR SEASONS", "HVAC BLOWER MOTOR"),
        ("DLA1005", "SMP", "DOOR LOCK ACTUATOR"),
        ("264-968", "DORMAN", "ENGINE VALVE COVER"),
    ]

    results_summary = []

    for part_number, brand, expected_category in test_parts:
        print(f"\n{'='*60}")
        print(f">> Testing: {brand} {part_number} (expected: {expected_category})")
        print("-" * 40)

        result = scraper.scrape_part(part_number, brand)

        status = "PASS" if result['found'] else "FAIL"
        cat_match = "YES" if result.get('category') == expected_category else "NO"

        print(f"  Status:    {status}")
        print(f"  Found:     {result['found']}")
        print(f"  Desc:      {result.get('description', 'N/A')}")
        print(f"  Price:     {result.get('price', 'N/A')}")
        print(f"  Brand:     {result.get('brand', 'N/A')}")
        print(f"  Category:  {result.get('category', 'N/A')} (match: {cat_match})")
        print(f"  Stock:     {result.get('availability', 'N/A')} (qty: {result.get('stock_quantity', 'N/A')})")
        print(f"  Image:     {'YES' if result.get('image_url') else 'NO'}")
        print(f"  Fitment:   {len(result.get('fitment_data', []))} records")
        print(f"  Specs:     {len(result.get('specs', {}))} attributes")

        if result.get('error'):
            print(f"  Error:     {result['error']}")

        if result.get('fitment_data'):
            print(f"  Sample fitment:")
            for fit in result['fitment_data'][:3]:
                yr = f"{fit['year_start']}-{fit['year_end']}" if fit['year_start'] != fit['year_end'] else str(fit['year_start'])
                eng = f" ({fit['engine']})" if fit.get('engine') else ""
                print(f"    {yr} {fit['make']} {fit['model']}{eng}")

        results_summary.append((brand, part_number, status, result.get('category')))

    print(f"\n{'='*60}")
    print("SUMMARY")
    print("-" * 40)
    passed = sum(1 for _, _, s, _ in results_summary if s == "PASS")
    print(f"Results: {passed}/{len(results_summary)} parts found")
    for brand, pn, status, cat in results_summary:
        print(f"  {status}: {brand} {pn} -> {cat or 'N/A'}")


if __name__ == "__main__":
    test_partsgeek_scraper()
