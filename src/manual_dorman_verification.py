#!/usr/bin/env python3
"""
Manual verification of Dorman Products website structure and part search
"""

from playwright.sync_api import sync_playwright
import time

def verify_dorman_manually():
    """Manually explore Dorman site structure"""
    print("MANUAL DORMAN SITE EXPLORATION")
    print("=" * 40)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # Visible browser
        page = browser.new_page()

        try:
            print("1. Loading Dorman homepage...")
            response = page.goto("https://www.dormanproducts.com/", timeout=30000)
            print(f"   Status: {response.status}")

            # Wait for page to load
            page.wait_for_load_state("networkidle", timeout=10000)

            # Get page title
            title = page.title()
            print(f"   Title: {title}")

            # Look for search functionality
            print("\n2. Looking for search functionality...")

            # Try to find search elements
            search_elements = [
                "input[type='search']",
                "input[name='keyword']",
                "input[name='search']",
                "#search",
                ".search",
                "[placeholder*='search' i]",
                "[placeholder*='part' i]"
            ]

            found_search = None
            for selector in search_elements:
                element = page.query_selector(selector)
                if element:
                    placeholder = element.get_attribute("placeholder") or ""
                    name = element.get_attribute("name") or ""
                    print(f"   Found search: {selector} (placeholder: '{placeholder}', name: '{name}')")
                    found_search = selector
                    break

            if found_search:
                print(f"\n3. Testing search with selector: {found_search}")

                # Test with a simple term first
                search_input = page.query_selector(found_search)
                search_input.fill("door handle")
                print("   Filled search with 'door handle'")

                # Look for search button or try Enter
                search_buttons = [
                    "input[type='submit']",
                    "button[type='submit']",
                    ".search-button",
                    "#search-button",
                    "button:has-text('Search')"
                ]

                search_button = None
                for btn_selector in search_buttons:
                    btn = page.query_selector(btn_selector)
                    if btn:
                        print(f"   Found search button: {btn_selector}")
                        search_button = btn_selector
                        break

                if search_button:
                    page.query_selector(search_button).click()
                else:
                    search_input.press("Enter")

                print("   Search submitted, waiting for results...")
                time.sleep(5)

                # Check results
                current_url = page.url
                print(f"   Results URL: {current_url}")

                # Look for products or results
                result_selectors = [
                    ".product",
                    ".part",
                    ".search-result",
                    "[data-part]",
                    "tr[data-part-number]"
                ]

                results_found = []
                for selector in result_selectors:
                    elements = page.query_selector_all(selector)
                    if elements:
                        print(f"   Found {len(elements)} results with selector: {selector}")

                        # Try to extract part numbers from first few results
                        for i, element in enumerate(elements[:3]):
                            try:
                                text = element.inner_text()[:100]
                                # Look for Dorman part number patterns
                                import re
                                part_matches = re.findall(r'\b\d{3}-\d{3}\b', text)
                                if part_matches:
                                    results_found.extend(part_matches)
                                    print(f"     Result {i+1}: {text} -> Parts: {part_matches}")
                            except:
                                pass

                if results_found:
                    print(f"\n4. Found potential part numbers: {results_found[:5]}")
                else:
                    print(f"\n4. No part numbers extracted, checking page content...")
                    body_text = page.inner_text("body")[:1000]
                    print(f"   Page content preview: {body_text}")

            else:
                print("\n   No search functionality found")
                print("   Exploring page links...")

                # Look for product category links
                links = page.query_selector_all("a[href*='product'], a[href*='part'], a[href*='category']")
                print(f"   Found {len(links)} product/part related links")

                if links:
                    first_link = links[0]
                    href = first_link.get_attribute("href")
                    text = first_link.inner_text()[:50]
                    print(f"   First link: {text} -> {href}")

            print("\nKeeping browser open for 30 seconds for manual inspection...")
            time.sleep(30)

        except Exception as e:
            print(f"Error during exploration: {e}")

        finally:
            browser.close()

if __name__ == "__main__":
    verify_dorman_manually()