#!/usr/bin/env python3
"""
Debug ACDelco catalog to understand why parts aren't being found
"""

from playwright.sync_api import sync_playwright
import time


def debug_catalog_content():
    """Debug the catalog content to see what's available"""
    print("DEBUGGING ACDELCO CATALOG")
    print("=" * 40)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        try:
            # Navigate to catalog
            catalog_url = "https://parts.gmparts.com/categories/brake-system/brake-pads-shoes/"
            print(f"Loading: {catalog_url}")

            page.goto(catalog_url, timeout=30000)
            time.sleep(5)

            print(f"Page title: {page.title()}")
            print(f"Final URL: {page.url}")

            # Get page content
            page_text = page.inner_text("body")
            print(f"Content length: {len(page_text)} characters")

            # Look for any part numbers in the format we expect
            import re
            all_part_numbers = re.findall(r'\b\d{8,11}\b', page_text)
            unique_parts = list(set(all_part_numbers))[:10]

            print(f"Found part numbers on page: {unique_parts}")

            # Check specifically for our test parts
            test_parts = ["12735811", "84801575", "19474058", "88866309", "19367762"]
            found_test_parts = []

            for part in test_parts:
                if part in page_text:
                    found_test_parts.append(part)
                    print(f"✓ Found test part: {part}")

            if not found_test_parts:
                print("✗ None of our test parts found on this catalog page")
                print("\nLet's check what product links are available:")

                # Look for product links
                product_links = page.query_selector_all("a[href*='product']")
                print(f"Found {len(product_links)} product links")

                for i, link in enumerate(product_links[:5]):
                    href = link.get_attribute("href")
                    text = link.inner_text().strip()
                    print(f"  {i+1}. {text[:50]}... -> {href}")

            else:
                print(f"Found {len(found_test_parts)} of our test parts")

            # Try a different approach - look for search functionality
            print("\nChecking for search functionality...")
            search_inputs = page.query_selector_all("input[type='search'], input[name='search'], input[name='q']")

            if search_inputs:
                print(f"Found {len(search_inputs)} search inputs")
                # Try searching for one of our parts
                search_input = search_inputs[0]
                print("Trying search for part 12735811...")

                search_input.fill("12735811")
                search_input.press("Enter")
                time.sleep(5)

                search_results = page.inner_text("body")
                if "12735811" in search_results:
                    print("✓ Part found via search!")

                    # Look for product links in search results
                    product_links = page.query_selector_all("a[href*='product']")
                    for link in product_links[:2]:
                        href = link.get_attribute("href")
                        if "12735811" in href:
                            print(f"Product URL: {href}")
                            break
                else:
                    print("✗ Part not found in search results either")

        except Exception as e:
            print(f"Debug error: {e}")

        finally:
            browser.close()


def test_direct_product_url():
    """Test if we can construct product URLs directly"""
    print("\n" + "=" * 40)
    print("TESTING DIRECT PRODUCT URL CONSTRUCTION")

    # Based on our earlier analysis, the URL pattern was:
    # https://parts.gmparts.com/product/acdelco-gm-original-equipment-engine-oil-filter-12735811

    test_urls = [
        "https://parts.gmparts.com/product/acdelco-gm-original-equipment-engine-oil-filter-12735811",
        "https://parts.gmparts.com/product/12735811",
        "https://www.gmparts.com/p-12735811.aspx",
        "https://parts.gmparts.com/search?q=12735811"
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        try:
            for url in test_urls:
                print(f"\nTesting URL: {url}")
                try:
                    response = page.goto(url, timeout=20000)
                    print(f"  Status: {response.status}")
                    print(f"  Title: {page.title()}")

                    if response.status == 200:
                        content = page.inner_text("body")
                        if "12735811" in content:
                            print(f"  ✓ Part found! Content length: {len(content)}")
                            print(f"  URL works: {page.url}")
                            break
                        else:
                            print(f"  - Page loaded but part not found")
                    else:
                        print(f"  ✗ HTTP error")

                except Exception as e:
                    print(f"  ✗ Error: {e}")

        except Exception as e:
            print(f"Error testing URLs: {e}")

        finally:
            browser.close()


if __name__ == "__main__":
    debug_catalog_content()
    test_direct_product_url()