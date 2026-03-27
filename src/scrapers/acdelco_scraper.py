#!/usr/bin/env python3
"""
ACDelco/GMParts Scraper
Handles gmparts.com redirect and extracts comprehensive part data including fitment
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


class ACDelcoScraper:
    """Scraper for ACDelco parts via GMParts.com"""

    def __init__(self, headless: bool = True):
        """Initialize ACDelco scraper

        Args:
            headless: Whether to run browser in headless mode
        """
        self.headless = headless
        self.logger = logging.getLogger(__name__)
        self.base_catalog_url = "https://parts.gmparts.com/categories/brake-system/brake-pads-shoes/"

    def scrape_part(self, part_number: str, brand: str, config: Dict = None) -> Dict[str, Any]:
        """Scrape ACDelco part data following standardized interface

        Args:
            part_number: GM part number to search (e.g., "12735811")
            brand: Brand name (usually "ACDelco" or "GM")
            config: Site configuration (rate limits, etc.)

        Returns:
            Dict: Standardized scraping results
        """
        result = {
            'success': False,
            'found': False,
            'site_name': 'ACDelco',
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
            'fitment_data': [],  # Additional field for fitment
            'error': None
        }

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=self.headless)
                page = browser.new_page()

                # Set realistic user agent
                page.set_extra_http_headers({
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                })

                try:
                    # Step 1: Find product via catalog navigation (from pre-code review)
                    product_url = self._find_product_url(page, part_number)

                    if not product_url:
                        result['error'] = f"Product page not found for part {part_number}"
                        return result

                    # Step 2: Navigate to product page
                    print(f"[ACDelco] Loading product page: {product_url}")
                    response = page.goto(product_url, timeout=30000)

                    if response.status != 200:
                        result['error'] = f"Failed to load product page: HTTP {response.status}"
                        return result

                    time.sleep(3)  # Allow page to fully load

                    # Step 3: Extract all data fields
                    result['product_url'] = product_url
                    result['success'] = True

                    self._extract_part_number(page, result)
                    self._extract_product_name_and_description(page, result)
                    self._extract_brand_info(page, result)
                    self._extract_pricing(page, result)
                    self._extract_oem_references(page, result)
                    self._extract_images(page, result)
                    self._extract_availability(page, result)
                    self._extract_specifications(page, result)
                    self._extract_fitment_data(page, result)  # CRITICAL for fitment table

                    # Apply Unicode sanitization to all scraped data
                    result = self._sanitize_result_data(result)

                    # Determine if part was actually found
                    result['found'] = (
                        result['part_number'] is not None or
                        result['description'] is not None or
                        len(result['fitment_data']) > 0
                    )

                    if result['found']:
                        safe_desc = sanitize_unicode_text(result.get('description', 'N/A'))
                        print(f"[ACDelco] Successfully scraped part {part_number}")
                        print(f"          Title: {safe_desc[:50]}...")
                        print(f"          Price: {result.get('price', 'N/A')}")
                        print(f"          OEM Refs: {len(result.get('oem_refs', []))}")
                        print(f"          Fitment Records: {len(result.get('fitment_data', []))}")
                    else:
                        result['error'] = "Product page found but no data extracted"

                except Exception as e:
                    result['error'] = f"Scraping error: {str(e)}"
                    self.logger.error(f"ACDelco scraping error for {part_number}: {e}")

                finally:
                    browser.close()

        except Exception as e:
            result['error'] = f"Browser error: {str(e)}"
            self.logger.error(f"ACDelco browser error: {e}")

        return result

    def _sanitize_result_data(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Apply Unicode sanitization to all scraped data to prevent crashes

        Args:
            result: Raw scraping results that may contain problematic Unicode

        Returns:
            Dict: Sanitized results safe for storage and display
        """
        try:
            # Sanitize the entire result dictionary recursively
            sanitized_result = sanitize_unicode_dict(result)

            # Extra safety for critical fields
            if 'description' in sanitized_result and sanitized_result['description']:
                sanitized_result['description'] = sanitize_unicode_text(sanitized_result['description'])

            if 'error' in sanitized_result and sanitized_result['error']:
                sanitized_result['error'] = sanitize_unicode_text(sanitized_result['error'])

            # Sanitize OEM references list
            if 'oem_refs' in sanitized_result and isinstance(sanitized_result['oem_refs'], list):
                sanitized_result['oem_refs'] = [
                    sanitize_unicode_text(ref) for ref in sanitized_result['oem_refs']
                    if ref is not None
                ]

            # Sanitize fitment data
            if 'fitment_data' in sanitized_result and isinstance(sanitized_result['fitment_data'], list):
                sanitized_fitment = []
                for fitment in sanitized_result['fitment_data']:
                    if isinstance(fitment, dict):
                        clean_fitment = {
                            'year': fitment.get('year'),
                            'make': sanitize_unicode_text(str(fitment.get('make', ''))),
                            'model': sanitize_unicode_text(str(fitment.get('model', ''))),
                            'engine': sanitize_unicode_text(str(fitment.get('engine', ''))) if fitment.get('engine') else None
                        }
                        sanitized_fitment.append(clean_fitment)
                sanitized_result['fitment_data'] = sanitized_fitment

            return sanitized_result

        except Exception as e:
            self.logger.error(f"Error sanitizing result data: {e}")
            # Return original result if sanitization fails
            return result

    def _find_product_url(self, page, part_number: str) -> Optional[str]:
        """Find product URL using search functionality (more reliable than catalog)

        Args:
            page: Playwright page object
            part_number: GM part number to find

        Returns:
            str: Product URL if found, None otherwise
        """
        try:
            # Navigate to GM Parts main page and use search
            print(f"[ACDelco] Searching for part {part_number} via site search")
            page.goto("https://parts.gmparts.com/", timeout=30000)
            time.sleep(3)

            # Look for search functionality
            search_selectors = [
                "input[type='search']",
                "input[name='search']",
                "input[name='q']",
                "#search",
                ".search-input",
                "input[placeholder*='search' i]"
            ]

            search_input = None
            for selector in search_selectors:
                element = page.query_selector(selector)
                if element:
                    search_input = element
                    print(f"[ACDelco] Found search input: {selector}")
                    break

            if search_input:
                # Search for the part number
                search_input.fill(part_number)
                search_input.press("Enter")
                time.sleep(5)

                # Check if we got search results with our part
                results_text = page.inner_text("body")
                if part_number in results_text:
                    print(f"[ACDelco] Found part {part_number} in search results")

                    # Look for product links in the search results
                    product_links = page.query_selector_all("a[href*='product']")
                    for link in product_links:
                        href = link.get_attribute("href")
                        link_text = link.inner_text().strip()

                        # Check if this link is for our part
                        if href and (part_number in href or part_number in link_text):
                            if href.startswith("/"):
                                href = "https://parts.gmparts.com" + href
                            print(f"[ACDelco] Found product URL: {href}")
                            return href

                    # Fallback: Look for any product links and test them
                    for link in product_links[:3]:  # Test first few links
                        href = link.get_attribute("href")
                        if href:
                            if href.startswith("/"):
                                href = "https://parts.gmparts.com" + href

                            # Test if this link contains our part
                            try:
                                test_response = page.goto(href, timeout=15000)
                                if test_response.status == 200:
                                    time.sleep(2)
                                    test_content = page.inner_text("body")
                                    if part_number in test_content:
                                        print(f"[ACDelco] Verified product URL: {href}")
                                        return href

                                # Go back to search results
                                page.go_back()
                                time.sleep(2)
                            except:
                                continue

                else:
                    print(f"[ACDelco] Part {part_number} not found in search results")

            else:
                print(f"[ACDelco] No search input found on page")

            # Ultimate fallback: try catalog approach
            return self._fallback_catalog_search(page, part_number)

        except Exception as e:
            print(f"[ACDelco] Error in search approach: {e}")
            return self._fallback_catalog_search(page, part_number)

    def _fallback_catalog_search(self, page, part_number: str) -> Optional[str]:
        """Fallback catalog search method"""
        try:
            print(f"[ACDelco] Trying fallback catalog search for {part_number}")

            # Go to catalog page
            page.goto(self.base_catalog_url, timeout=30000)
            time.sleep(3)

            # Check if part is in catalog
            page_text = page.inner_text("body")
            if part_number not in page_text:
                print(f"[ACDelco] Part {part_number} not in catalog")
                return None

            print(f"[ACDelco] Part {part_number} found in catalog, looking for links...")

            # Try clicking on product elements containing the part number
            # Look for any element that contains the part number and try to find associated links
            all_elements = page.query_selector_all("*")

            for element in all_elements:
                try:
                    element_text = element.inner_text()
                    if part_number in element_text:
                        # Look for links within this element or its parent
                        links = element.query_selector_all("a")
                        if not links:
                            # Check parent element for links
                            parent = element.query_selector("..")
                            if parent:
                                links = parent.query_selector_all("a")

                        for link in links:
                            href = link.get_attribute("href")
                            if href and ("product" in href or "part" in href.lower()):
                                if href.startswith("/"):
                                    href = "https://parts.gmparts.com" + href
                                print(f"[ACDelco] Found potential product link: {href}")
                                return href

                        # If this element has a click handler, try clicking it
                        if element.is_visible():
                            try:
                                element.click()
                                time.sleep(3)
                                new_url = page.url
                                if new_url != self.base_catalog_url and part_number in page.inner_text("body"):
                                    print(f"[ACDelco] Clicked to product page: {new_url}")
                                    return new_url
                            except:
                                continue
                        break

                except:
                    continue

            return None

        except Exception as e:
            print(f"[ACDelco] Fallback catalog search error: {e}")
            return None

    def _extract_part_number(self, page, result: Dict) -> None:
        """Extract GM part number from page"""
        try:
            page_text = page.inner_text("body")

            # Look for "GM Part # 12735811" pattern
            gm_part_match = re.search(r'GM Part #\s*([0-9]+)', page_text)
            if gm_part_match:
                result['part_number'] = gm_part_match.group(1)

        except Exception as e:
            self.logger.error(f"Error extracting part number: {e}")

    def _extract_product_name_and_description(self, page, result: Dict) -> None:
        """Extract product name and description"""
        try:
            # Product name from H1 tag (from pre-code review)
            h1_element = page.query_selector("h1")
            if h1_element:
                product_name = h1_element.inner_text().strip()
                result['description'] = product_name

                # Extract category from product name
                if "Oil Filter" in product_name:
                    result['category'] = "Oil Filter"
                elif "Air Filter" in product_name:
                    result['category'] = "Air Filter"
                elif "Brake" in product_name:
                    result['category'] = "Brake Parts"
                elif "Engine" in product_name:
                    result['category'] = "Engine Parts"

            # Additional description text
            page_text = page.inner_text("body")
            desc_match = re.search(r'(Helps keep abrasive particles[^.]+\.)', page_text)
            if desc_match:
                additional_desc = desc_match.group(1)
                if result['description']:
                    result['description'] += f" - {additional_desc}"
                else:
                    result['description'] = additional_desc

        except Exception as e:
            self.logger.error(f"Error extracting product name: {e}")

    def _extract_brand_info(self, page, result: Dict) -> None:
        """Extract brand information"""
        try:
            page_text = page.inner_text("body")

            # Determine brand priority (from pre-code review)
            if "ACDelco GM Original Equipment" in page_text:
                result['brand'] = "ACDelco GM Original Equipment"
            elif "GM Genuine Parts" in page_text:
                result['brand'] = "GM Genuine Parts"
            elif "ACDelco" in page_text:
                result['brand'] = "ACDelco"
            elif "GM" in page_text:
                result['brand'] = "GM"

        except Exception as e:
            self.logger.error(f"Error extracting brand info: {e}")

    def _extract_pricing(self, page, result: Dict) -> None:
        """Extract pricing information"""
        try:
            # MSRP from .msrp selector (from pre-code review)
            msrp_element = page.query_selector(".msrp")
            if msrp_element:
                result['price'] = msrp_element.inner_text().strip()
            else:
                # Fallback: regex search for MSRP
                page_text = page.inner_text("body")
                price_match = re.search(r'MSRP[^\$]*\$([0-9,]+\.?\d*)', page_text)
                if price_match:
                    result['price'] = f"${price_match.group(1)}"

        except Exception as e:
            self.logger.error(f"Error extracting pricing: {e}")

    def _extract_oem_references(self, page, result: Dict) -> None:
        """Extract OEM cross-references (CRITICAL for oem_references table)"""
        try:
            page_text = page.inner_text("body")

            # Extract ACDelco part number (from pre-code review: "ACDelco Part # PF63")
            acdelco_match = re.search(r'ACDelco Part #\s*([A-Z0-9-]+)', page_text)
            if acdelco_match:
                oem_part = acdelco_match.group(1)
                result['oem_refs'] = [oem_part]

            # Look for other OEM patterns
            oem_patterns = [
                r'OEM[^:]*:\s*([A-Z0-9-]+)',
                r'Replaces[^:]*:\s*([A-Z0-9-]+)',
                r'Cross Reference[^:]*:\s*([A-Z0-9-]+)'
            ]

            for pattern in oem_patterns:
                matches = re.findall(pattern, page_text)
                for match in matches:
                    if match not in result['oem_refs']:
                        result['oem_refs'].append(match)

        except Exception as e:
            self.logger.error(f"Error extracting OEM references: {e}")

    def _extract_images(self, page, result: Dict) -> None:
        """Extract product images"""
        try:
            # Product images from GM assets (from pre-code review)
            image_selectors = [
                "img[src*='ecommerce-assets.ext.gm.com']",
                "img[alt*='ACDelco']",
                "img[alt*='GM']"
            ]

            for selector in image_selectors:
                images = page.query_selector_all(selector)
                for img in images:
                    src = img.get_attribute("src")
                    alt = img.get_attribute("alt")
                    if src and "Warning_sign" not in src and "logo" not in src:
                        result['image_url'] = src
                        break
                if result['image_url']:
                    break

        except Exception as e:
            self.logger.error(f"Error extracting images: {e}")

    def _extract_availability(self, page, result: Dict) -> None:
        """Extract availability/stock information"""
        try:
            page_text = page.inner_text("body")

            if "CURRENT SELLER" in page_text:
                result['availability'] = "Available from Multiple Sellers"
            elif "Select Seller" in page_text:
                result['availability'] = "Select Seller Required"
            elif "Available" in page_text:
                result['availability'] = "Available"
            elif "Out of Stock" in page_text:
                result['availability'] = "Out of Stock"
            else:
                result['availability'] = "Unknown"

        except Exception as e:
            self.logger.error(f"Error extracting availability: {e}")

    def _extract_specifications(self, page, result: Dict) -> None:
        """Extract technical specifications for part_specs table"""
        try:
            page_text = page.inner_text("body")

            # Look for specifications in common patterns
            spec_patterns = {
                'Filter Type': r'Filter Type[:\s]*([^.\n]+)',
                'Thread Size': r'Thread Size[:\s]*([^.\n]+)',
                'Height': r'Height[:\s]*([0-9.]+ ?[a-zA-Z]+)',
                'Diameter': r'Diameter[:\s]*([0-9.]+ ?[a-zA-Z]+)',
                'Material': r'Material[:\s]*([^.\n]+)',
                'Application': r'Application[:\s]*([^.\n]+)'
            }

            for spec_name, pattern in spec_patterns.items():
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    spec_value = match.group(1).strip()
                    if spec_value and len(spec_value) < 100:  # Reasonable spec value
                        result['specs'][spec_name] = spec_value

            # Additional specifications from product details
            if "dexos" in page_text.lower():
                result['specs']['Oil Standard'] = 'dexos'

            if "Full Synthetic" in page_text:
                result['specs']['Oil Type'] = 'Full Synthetic'

        except Exception as e:
            self.logger.error(f"Error extracting specifications: {e}")

    def _extract_fitment_data(self, page, result: Dict) -> None:
        """Extract fitment data for fitment table (CRITICAL - solves 0 rows problem)"""
        try:
            page_text = page.inner_text("body")

            # Extract the massive fitment string (from pre-code review discovery)
            fitment_match = re.search(r'Fits - ([^.]+\.)', page_text)
            if fitment_match:
                fitment_text = fitment_match.group(1)
                print(f"[ACDelco] Found fitment data: {fitment_text[:100]}...")

                # Parse fitment entries: "2011-2024 Buick Enclave ; 2016-2019 Cadillac ATS ; ..."
                fitment_entries = []

                for item in fitment_text.split(' ; '):
                    item = item.strip()
                    if not item:
                        continue

                    try:
                        # Parse format: "2011-2024 Buick Enclave"
                        parts = item.split()
                        if len(parts) >= 3:
                            year_range = parts[0]
                            make = parts[1]
                            model = ' '.join(parts[2:])

                            # Expand year range
                            years = self._expand_year_range(year_range)

                            for year in years:
                                fitment_entries.append({
                                    'year': year,
                                    'make': make,
                                    'model': model,
                                    'engine': None  # Not specified in GMParts data
                                })

                    except Exception as e:
                        self.logger.error(f"Error parsing fitment item '{item}': {e}")
                        continue

                result['fitment_data'] = fitment_entries
                print(f"[ACDelco] Parsed {len(fitment_entries)} fitment records")

            else:
                print(f"[ACDelco] No fitment data found in page content")

        except Exception as e:
            self.logger.error(f"Error extracting fitment data: {e}")

    def _expand_year_range(self, year_range: str) -> List[int]:
        """Expand year range string to list of years

        Args:
            year_range: Year range like "2011-2024" or single year "2020"

        Returns:
            List[int]: List of individual years
        """
        try:
            if '-' in year_range:
                start_year, end_year = year_range.split('-')
                return list(range(int(start_year), int(end_year) + 1))
            else:
                return [int(year_range)]
        except (ValueError, AttributeError):
            return []


def test_acdelco_scraper():
    """Test the ACDelco scraper with verified parts"""
    print("TESTING ACDELCO SCRAPER")
    print("=" * 50)

    scraper = ACDelcoScraper(headless=False)  # Visible for debugging

    # Test with verified parts from pre-code review
    test_parts = [
        ("12735811", "ACDelco"),  # Oil Filter - confirmed working
        ("84801575", "ACDelco"),
        ("19474058", "ACDelco")
    ]

    for part_number, brand in test_parts:
        print(f"\n>> Testing Part: {part_number}")
        print("-" * 30)

        result = scraper.scrape_part(part_number, brand)

        print(f"Success: {result['success']}")
        print(f"Found: {result['found']}")
        print(f"Description: {result.get('description', 'N/A')}")
        print(f"Price: {result.get('price', 'N/A')}")
        print(f"OEM Refs: {result.get('oem_refs', [])}")
        print(f"Fitment Records: {len(result.get('fitment_data', []))}")

        if result.get('error'):
            print(f"Error: {result['error']}")

        if result.get('fitment_data'):
            print("Sample Fitment:")
            for i, fit in enumerate(result['fitment_data'][:3]):
                print(f"  {fit['year']} {fit['make']} {fit['model']}")


if __name__ == "__main__":
    test_acdelco_scraper()