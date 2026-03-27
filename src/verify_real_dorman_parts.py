#!/usr/bin/env python3
"""
Find and verify REAL part numbers from live DormanProducts.com site
"""

from playwright.sync_api import sync_playwright
import time
import re

def find_real_dorman_parts():
    """Navigate to Dorman site and extract real part numbers from live content"""
    print("FINDING REAL DORMAN PART NUMBERS FROM LIVE SITE")
    print("=" * 60)

    verified_parts = []

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,  # Visible to see what's happening
            args=["--disable-blink-features=AutomationControlled"]
        )

        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        )
        page = context.new_page()

        try:
            # Step 1: Load homepage
            print("1. Loading Dorman homepage...")
            response = page.goto("https://www.dormanproducts.com/", timeout=45000)
            print(f"   Homepage status: {response.status}")

            if response.status != 200:
                print(f"   ERROR: Homepage failed with status {response.status}")
                return []

            # Wait for page to fully load
            page.wait_for_load_state("networkidle", timeout=30000)

            # Step 2: Look for search functionality
            print("\n2. Looking for search functionality...")

            search_selectors = [
                "input[name='keyword']",
                "input[type='search']",
                "#searchBox",
                ".search-input",
                "[placeholder*='search' i]",
                "[placeholder*='part' i]",
                "input[name='q']"
            ]

            search_input = None
            for selector in search_selectors:
                element = page.query_selector(selector)
                if element:
                    print(f"   Found search input: {selector}")
                    search_input = element
                    break

            if not search_input:
                print("   No search input found. Trying to find product navigation...")

                # Look for product category links
                nav_links = page.query_selector_all("a[href*='product'], a[href*='catalog'], a[href*='parts']")
                if nav_links:
                    first_nav = nav_links[0]
                    nav_url = first_nav.get_attribute("href")
                    nav_text = first_nav.inner_text()
                    print(f"   Found navigation link: {nav_text} -> {nav_url}")

                    # Navigate to product section
                    if nav_url.startswith('/'):
                        nav_url = "https://www.dormanproducts.com" + nav_url

                    page.goto(nav_url, timeout=30000)
                    page.wait_for_load_state("networkidle", timeout=15000)

                    # Try to find parts on this page
                    verified_parts.extend(extract_parts_from_current_page(page))

            else:
                # Step 3: Perform searches for common parts
                print("\n3. Performing searches for real parts...")

                search_terms = [
                    "window regulator",
                    "door handle",
                    "power steering",
                    "radiator",
                    "control arm"
                ]

                for term in search_terms:
                    print(f"\n   Searching for: {term}")

                    try:
                        # Clear and fill search
                        search_input.clear()
                        search_input.fill(term)

                        # Submit search
                        search_input.press("Enter")

                        # Wait for results
                        time.sleep(5)
                        page.wait_for_load_state("networkidle", timeout=10000)

                        print(f"   Search results URL: {page.url}")

                        # Extract parts from results
                        parts_found = extract_parts_from_current_page(page)
                        verified_parts.extend(parts_found)

                        if len(verified_parts) >= 5:
                            break

                    except Exception as e:
                        print(f"   Search error for '{term}': {e}")
                        continue

            # Step 4: Verify each part has a real product page
            print(f"\n4. Verifying {len(verified_parts)} found parts have real product pages...")

            final_verified = []
            for part_info in verified_parts[:10]:  # Test up to 10 to get 5 good ones
                part_num = part_info['part_number']
                print(f"\n   Verifying {part_num}...")

                # Try different URL patterns for product pages
                test_urls = [
                    f"https://www.dormanproducts.com/p-{part_num}.aspx",
                    f"https://www.dormanproducts.com/gsearch.aspx?keyword={part_num}",
                    part_info.get('product_url', '')
                ]

                for test_url in test_urls:
                    if not test_url:
                        continue

                    try:
                        response = page.goto(test_url, timeout=15000)
                        if response.status == 200:
                            page.wait_for_load_state("networkidle", timeout=5000)

                            # Check if this is actually a product page
                            page_content = page.inner_text("body").lower()

                            if (part_num.lower() in page_content and
                                any(word in page_content for word in ['product', 'part', 'description', 'specification'])):

                                part_info['verified_url'] = test_url
                                final_verified.append(part_info)
                                print(f"     ✓ VERIFIED: {part_num} at {test_url}")
                                break
                    except:
                        continue

                if len(final_verified) >= 5:
                    break

            print(f"\n" + "=" * 60)
            print("VERIFIED REAL DORMAN PART NUMBERS:")
            print("-" * 35)

            if final_verified:
                for i, part in enumerate(final_verified, 1):
                    print(f"{i}. {part['part_number']} - {part['description']}")
                    print(f"   URL: {part['verified_url']}")
                    print()
            else:
                print("ERROR: No parts could be verified on live site")

            # Keep browser open for manual verification
            if final_verified:
                print("SUCCESS: Keeping browser open for 30 seconds for manual verification...")
                print("Please manually check that these part pages are real and working.")
                time.sleep(30)

            return final_verified

        except Exception as e:
            print(f"ERROR during site exploration: {e}")
            import traceback
            traceback.print_exc()
            return []

        finally:
            browser.close()

def extract_parts_from_current_page(page):
    """Extract part numbers from current page content"""
    parts_found = []

    try:
        # Get page content
        page_content = page.content()
        page_text = page.inner_text("body")

        # Look for Dorman part number patterns in various places
        # Common patterns: XXX-XXX, XXXXX-XX, XXX-XXXX
        part_patterns = [
            r'\b(\d{3}-\d{3})\b',      # 924-503
            r'\b(\d{5}-\d{2})\b',      # 12345-67
            r'\b(\d{3}-\d{4})\b',      # 924-5037
            r'\b(OES\d{5,8})\b',       # OES12345
            r'\b(DOR\d{5,8})\b'        # DOR12345
        ]

        found_numbers = set()

        for pattern in part_patterns:
            matches = re.findall(pattern, page_text, re.IGNORECASE)
            found_numbers.update(matches)

        print(f"     Found {len(found_numbers)} potential part numbers on page")

        # Try to extract more context for each part number
        for part_num in list(found_numbers)[:10]:  # Limit to first 10
            try:
                # Look for links containing this part number
                part_links = page.query_selector_all(f"a[href*='{part_num}']")

                description = "Unknown"
                product_url = ""

                if part_links:
                    link = part_links[0]
                    product_url = link.get_attribute("href")
                    if product_url and product_url.startswith('/'):
                        product_url = "https://www.dormanproducts.com" + product_url

                    # Try to get description from link text or nearby text
                    link_text = link.inner_text().strip()
                    if link_text and len(link_text) > len(part_num):
                        description = link_text[:100]

                parts_found.append({
                    'part_number': part_num,
                    'description': description,
                    'product_url': product_url,
                    'found_on_url': page.url
                })

            except Exception as e:
                print(f"     Error processing part {part_num}: {e}")

        return parts_found

    except Exception as e:
        print(f"   Error extracting parts from page: {e}")
        return []

if __name__ == "__main__":
    verified_parts = find_real_dorman_parts()

    print("\n" + "=" * 60)
    print("FINAL RESULTS FOR DORMAN SCRAPER TESTING:")
    print("-" * 40)

    if verified_parts:
        print(f"✓ Successfully found {len(verified_parts)} verified real part numbers")
        print("\nReady to proceed with Dorman scraper implementation.")
    else:
        print("✗ Could not verify any real part numbers from live site")
        print("Manual investigation required before proceeding.")