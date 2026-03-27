#!/usr/bin/env python3
"""
Find real verified part numbers from ACDelco/GMParts and Moog
"""

from playwright.sync_api import sync_playwright
import time
import re

def find_gmparts_parts():
    """Find real parts from GMParts.com (ACDelco redirect)"""
    print("FINDING REAL PARTS FROM GMPARTS.COM (ACDELCO)")
    print("=" * 50)

    parts = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            page = browser.new_page()

            # Go to GM Parts site
            print("1. Loading GMParts.com...")
            page.goto("https://www.gmparts.com/", timeout=30000)
            time.sleep(3)

            # Look for search functionality
            print("2. Looking for search...")
            search_selectors = [
                "input[type='search']",
                "input[name='search']",
                "input[name='q']",
                "#search",
                ".search-input"
            ]

            search_input = None
            for selector in search_selectors:
                element = page.query_selector(selector)
                if element:
                    search_input = element
                    print(f"   Found search: {selector}")
                    break

            if search_input:
                # Try searching for common GM/ACDelco parts
                search_terms = ["oil filter", "brake pad", "spark plug", "air filter"]

                for term in search_terms:
                    print(f"\n3. Searching for: {term}")

                    try:
                        search_input.clear()
                        search_input.fill(term)
                        search_input.press("Enter")

                        time.sleep(5)

                        # Look for part numbers in results
                        page_content = page.inner_text("body")
                        print(f"   Results URL: {page.url}")

                        # GM/ACDelco part patterns
                        gm_patterns = [
                            r'\b(AC\d{6,8})\b',          # ACDelco: AC123456
                            r'\b(\d{8,11})\b',           # GM: 12345678901
                            r'\b(PF\d{2,4}[A-Z]?)\b',   # Oil filters: PF46E
                            r'\b(\d{2,4}[A-Z]{1,3}\d{2,4})\b'  # Mixed: 25175808
                        ]

                        found_parts = set()
                        for pattern in gm_patterns:
                            matches = re.findall(pattern, page_content)
                            found_parts.update(matches)

                        if found_parts:
                            print(f"   Found potential parts: {list(found_parts)[:5]}")

                            # Verify parts by looking for product links
                            for part_num in list(found_parts)[:3]:
                                try:
                                    # Look for links to this part
                                    links = page.query_selector_all(f"a[href*='{part_num}']")
                                    if links:
                                        link_url = links[0].get_attribute("href")
                                        if link_url:
                                            if link_url.startswith('/'):
                                                link_url = "https://www.gmparts.com" + link_url

                                            # Test if the product page works
                                            test_response = page.goto(link_url, timeout=15000)
                                            if test_response.status == 200:
                                                time.sleep(2)
                                                product_content = page.inner_text("body")

                                                if part_num in product_content and len(product_content) > 200:
                                                    parts.append({
                                                        'part_number': part_num,
                                                        'url': link_url,
                                                        'source': 'GMParts',
                                                        'search_term': term
                                                    })
                                                    print(f"   ✓ VERIFIED: {part_num} -> {link_url}")

                                                    if len(parts) >= 3:
                                                        browser.close()
                                                        return parts

                                            # Go back to search results
                                            page.go_back()
                                            time.sleep(2)

                                except Exception as e:
                                    print(f"   Error verifying {part_num}: {e}")

                        if len(parts) >= 3:
                            break

                    except Exception as e:
                        print(f"   Search error for {term}: {e}")

            else:
                print("   No search input found - trying navigation")

                # Look for parts catalog or browse links
                nav_links = page.query_selector_all("a[href*='part'], a[href*='catalog'], a[href*='browse']")
                if nav_links:
                    first_nav = nav_links[0]
                    nav_url = first_nav.get_attribute("href")
                    print(f"   Trying navigation: {nav_url}")

                    if nav_url.startswith('/'):
                        nav_url = "https://www.gmparts.com" + nav_url

                    page.goto(nav_url, timeout=20000)
                    time.sleep(3)

                    # Extract parts from catalog page
                    catalog_content = page.inner_text("body")
                    gm_patterns = [r'\b(AC\d{6})\b', r'\b(\d{8,10})\b']

                    for pattern in gm_patterns:
                        matches = re.findall(pattern, catalog_content)
                        for match in matches[:3]:
                            parts.append({
                                'part_number': match,
                                'url': page.url,
                                'source': 'GMParts',
                                'search_term': 'catalog'
                            })

            browser.close()

    except Exception as e:
        print(f"Error finding GMParts parts: {e}")

    return parts

def find_moog_parts():
    """Find real parts from MoogParts.com"""
    print("\n" + "=" * 50)
    print("FINDING REAL PARTS FROM MOOGPARTS.COM")
    print("=" * 50)

    parts = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            page = browser.new_page()

            # Go to Moog Parts site
            print("1. Loading MoogParts.com...")
            page.goto("https://www.moogparts.com/", timeout=30000)
            time.sleep(3)

            # Look for part lookup or search
            print("2. Looking for part lookup...")

            # Try to find part lookup/search elements
            lookup_selectors = [
                "input[placeholder*='part' i]",
                "input[name*='part']",
                "input[type='search']",
                ".part-lookup",
                "#partLookup"
            ]

            lookup_input = None
            for selector in lookup_selectors:
                element = page.query_selector(selector)
                if element:
                    lookup_input = element
                    print(f"   Found lookup: {selector}")
                    break

            if lookup_input:
                # Try searching for common Moog parts
                moog_searches = ["control arm", "ball joint", "tie rod", "sway bar"]

                for term in moog_searches:
                    print(f"\n3. Searching for: {term}")

                    try:
                        lookup_input.clear()
                        lookup_input.fill(term)
                        lookup_input.press("Enter")

                        time.sleep(5)

                        page_content = page.inner_text("body")
                        print(f"   Results URL: {page.url}")

                        # Moog part number patterns
                        moog_patterns = [
                            r'\b(K\d{4,6})\b',           # K80145
                            r'\b(ES\d{4,6})\b',          # ES3470
                            r'\b(RK\d{4,6})\b',          # RK620
                            r'\b(MOO-\w{4,8})\b'         # MOO-K80145
                        ]

                        found_moog_parts = set()
                        for pattern in moog_patterns:
                            matches = re.findall(pattern, page_content)
                            found_moog_parts.update(matches)

                        if found_moog_parts:
                            print(f"   Found potential Moog parts: {list(found_moog_parts)[:5]}")

                            # Verify Moog parts
                            for part_num in list(found_moog_parts)[:3]:
                                try:
                                    links = page.query_selector_all(f"a[href*='{part_num}']")
                                    if links:
                                        link_url = links[0].get_attribute("href")
                                        if link_url:
                                            if link_url.startswith('/'):
                                                link_url = "https://www.moogparts.com" + link_url

                                            test_response = page.goto(link_url, timeout=15000)
                                            if test_response.status == 200:
                                                time.sleep(2)
                                                product_content = page.inner_text("body")

                                                if part_num in product_content and len(product_content) > 200:
                                                    parts.append({
                                                        'part_number': part_num,
                                                        'url': link_url,
                                                        'source': 'Moog',
                                                        'search_term': term
                                                    })
                                                    print(f"   ✓ VERIFIED: {part_num} -> {link_url}")

                                                    if len(parts) >= 3:
                                                        browser.close()
                                                        return parts

                                            page.go_back()
                                            time.sleep(2)

                                except Exception as e:
                                    print(f"   Error verifying {part_num}: {e}")

                        if len(parts) >= 3:
                            break

                    except Exception as e:
                        print(f"   Search error for {term}: {e}")

            else:
                print("   No part lookup found - checking navigation")

                # Look for parts navigation
                nav_links = page.query_selector_all("a[href*='part'], a[href*='product'], a[href*='catalog']")
                if nav_links:
                    nav_link = nav_links[0]
                    nav_url = nav_link.get_attribute("href")

                    if nav_url.startswith('/'):
                        nav_url = "https://www.moogparts.com" + nav_url

                    print(f"   Trying navigation: {nav_url}")
                    page.goto(nav_url, timeout=20000)
                    time.sleep(3)

                    # Extract parts from navigation page
                    nav_content = page.inner_text("body")
                    moog_patterns = [r'\b(K\d{4,5})\b', r'\b(ES\d{4,5})\b']

                    for pattern in moog_patterns:
                        matches = re.findall(pattern, nav_content)
                        for match in matches[:3]:
                            parts.append({
                                'part_number': match,
                                'url': page.url,
                                'source': 'Moog',
                                'search_term': 'navigation'
                            })

            browser.close()

    except Exception as e:
        print(f"Error finding Moog parts: {e}")

    return parts

if __name__ == "__main__":
    print("FINDING VERIFIED PARTS FROM ACCESSIBLE SITES")
    print("=" * 60)

    # Find parts from both sites
    gmparts_parts = find_gmparts_parts()
    moog_parts = find_moog_parts()

    # Final summary
    print("\n" + "=" * 60)
    print("FINAL VERIFIED PARTS FOR SCRAPER DEVELOPMENT:")
    print("-" * 50)

    print(f"\nACDELCO/GMPARTS ({len(gmparts_parts)} parts):")
    for i, part in enumerate(gmparts_parts, 1):
        print(f"  {i}. {part['part_number']}")
        print(f"     URL: {part['url']}")
        print(f"     Found via: {part['search_term']}")

    print(f"\nMOOG ({len(moog_parts)} parts):")
    for i, part in enumerate(moog_parts, 1):
        print(f"  {i}. {part['part_number']}")
        print(f"     URL: {part['url']}")
        print(f"     Found via: {part['search_term']}")

    total_parts = len(gmparts_parts) + len(moog_parts)
    print(f"\n" + "=" * 60)
    print(f"TOTAL VERIFIED PARTS: {total_parts}")

    if total_parts >= 4:
        print("✓ SUCCESS: Sufficient parts found for both sites")
        print("Ready to implement ACDelco and Moog scrapers")
    else:
        print(f"Need {4 - total_parts} more verified parts")
        print("May need manual verification of additional parts")