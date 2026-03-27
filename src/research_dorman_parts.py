#!/usr/bin/env python3
"""
Research Dorman Products website to find test part numbers
"""

import requests
from playwright.sync_api import sync_playwright
import time
import re

def research_dorman_parts():
    """Research Dorman website for real part numbers"""
    print("DORMAN PRODUCTS PART NUMBER RESEARCH")
    print("=" * 50)

    # Known Dorman part number patterns (research from automotive forums):
    # Dorman typically uses patterns like:
    # - 6-digit numbers (924-XXX, 697-XXX)
    # - Some with letters (OE Solutions: 917-XXX)

    test_parts = [
        "924-503",   # Common window regulator part
        "697-318",   # Power steering reservoir
        "917-143",   # Intake manifold (OE Solutions)
        "620-430",   # Radiator support
        "746-018"    # Door handle
    ]

    print("Testing known Dorman part number patterns:")
    print("-" * 40)

    # Test with HTTP requests first (faster)
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
    })

    verified_parts = []

    for part_num in test_parts:
        try:
            # Try different URL patterns for Dorman
            search_urls = [
                f"https://www.dormanproducts.com/p-{part_num}.aspx",
                f"https://www.dormanproducts.com/gsearch.aspx?keyword={part_num}",
                f"https://www.dormanproducts.com/part/{part_num}",
            ]

            for url in search_urls:
                try:
                    response = session.get(url, timeout=10)
                    print(f"Testing {part_num} at {url}")
                    print(f"  Status: {response.status_code}")

                    if response.status_code == 200:
                        # Look for part number in content
                        content = response.text.lower()
                        if part_num.lower() in content and 'part' in content:
                            print(f"  ✓ FOUND: {part_num} exists!")
                            verified_parts.append({
                                'part_number': part_num,
                                'url': url,
                                'status': 'verified'
                            })
                            break
                        else:
                            print(f"  - Part number not found in content")
                    else:
                        print(f"  - HTTP {response.status_code}")

                except Exception as e:
                    print(f"  - Error: {e}")

            print()

        except Exception as e:
            print(f"Error testing {part_num}: {e}")

    # If HTTP method didn't find enough, try browser automation
    if len(verified_parts) < 3:
        print("\nTrying browser automation approach...")
        verified_parts.extend(browser_search_dorman())

    print("\n" + "=" * 50)
    print("VERIFIED DORMAN PART NUMBERS:")
    print("-" * 30)

    if verified_parts:
        for i, part in enumerate(verified_parts[:5], 1):
            print(f"{i}. {part['part_number']} - Status: {part['status']}")
    else:
        print("No parts verified - will use common automotive part patterns")
        # Fallback to commonly known Dorman parts
        fallback_parts = [
            "924-503",  # Window regulator clip
            "697-318",  # Power steering reservoir
            "620-430",  # Radiator support
            "746-018",  # Door handle
            "917-143"   # Intake manifold
        ]
        print("\nUsing known Dorman part patterns (unverified):")
        for i, part in enumerate(fallback_parts, 1):
            print(f"{i}. {part} - Common Dorman pattern")

        return fallback_parts

    return [part['part_number'] for part in verified_parts[:5]]

def browser_search_dorman():
    """Use browser to search for Dorman parts"""
    verified = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            # Try to access Dorman homepage
            response = page.goto("https://www.dormanproducts.com/", timeout=30000)
            print(f"Dorman homepage status: {response.status}")

            if response.status == 200:
                # Look for search functionality
                page.wait_for_load_state("networkidle")

                # Look for common search elements
                search_selectors = [
                    "input[type='search']",
                    "#search",
                    ".search-input",
                    "input[name*='search']",
                    "input[placeholder*='search']"
                ]

                search_found = False
                for selector in search_selectors:
                    if page.query_selector(selector):
                        print(f"Found search element: {selector}")
                        search_found = True
                        break

                if search_found:
                    # Try searching for a part
                    test_part = "924-503"
                    try:
                        search_input = page.query_selector(selector)
                        search_input.fill(test_part)
                        search_input.press("Enter")

                        page.wait_for_load_state("networkidle")
                        content = page.inner_text("body")

                        if test_part in content and "result" in content.lower():
                            verified.append({
                                'part_number': test_part,
                                'url': page.url,
                                'status': 'browser_verified'
                            })
                            print(f"Browser verified: {test_part}")

                    except Exception as e:
                        print(f"Browser search error: {e}")

            browser.close()

    except Exception as e:
        print(f"Browser automation error: {e}")

    return verified

if __name__ == "__main__":
    parts = research_dorman_parts()

    print(f"\nFINAL RESULT:")
    print(f"Found {len(parts)} test parts for Dorman scraper development:")
    for part in parts:
        print(f"  - {part}")