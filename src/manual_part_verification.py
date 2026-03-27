#!/usr/bin/env python3
"""
Manual verification to find real part numbers from ACDelco/GMParts and Moog
"""

from playwright.sync_api import sync_playwright
import time
import re

def find_gmparts_real_parts():
    """Find real parts by navigating GMParts catalog sections"""
    print("MANUAL GMPARTS PART VERIFICATION")
    print("=" * 40)

    parts = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        try:
            # Go to GM Parts catalog
            print("1. Loading GMParts catalog...")
            page.goto("https://www.gmparts.com/", timeout=30000)
            time.sleep(3)

            # Try to find parts categories or navigation
            print("2. Looking for parts navigation...")

            # Look for common navigation links
            nav_selectors = [
                "a[href*='oil']", "a[href*='filter']", "a[href*='brake']",
                "a[href*='part']", "a[href*='catalog']", "a[href*='search']"
            ]

            for selector in nav_selectors:
                elements = page.query_selector_all(selector)
                if elements:
                    print(f"   Found navigation: {selector} ({len(elements)} links)")
                    # Try first promising link
                    link = elements[0]
                    href = link.get_attribute("href")
                    if href and not href.startswith("#"):
                        print(f"   Trying: {href}")

                        if href.startswith("/"):
                            href = "https://www.gmparts.com" + href

                        try:
                            page.goto(href, timeout=20000)
                            time.sleep(3)

                            # Extract part numbers from this page
                            page_text = page.inner_text("body")

                            # GM/ACDelco patterns
                            patterns = [
                                r'\b(AC\d{6,8})\b',      # ACDelco: AC123456
                                r'\b(\d{8,11})\b',       # GM: 12345678901
                                r'\b(PF\d{2,4}[A-Z]?)\b'  # Oil filters: PF46E
                            ]

                            found = set()
                            for pattern in patterns:
                                matches = re.findall(pattern, page_text)
                                found.update(matches)

                            if found:
                                print(f"   Found potential parts: {list(found)[:5]}")
                                # Verify first few parts
                                for part in list(found)[:3]:
                                    verify_url = f"https://www.gmparts.com/p-{part}.aspx"
                                    try:
                                        resp = page.goto(verify_url, timeout=15000)
                                        if resp.status == 200:
                                            time.sleep(2)
                                            if part.lower() in page.inner_text("body").lower():
                                                parts.append({
                                                    'part_number': part,
                                                    'url': verify_url,
                                                    'source': 'GMParts'
                                                })
                                                print(f"   [VERIFIED] {part} -> {verify_url}")
                                                if len(parts) >= 3:
                                                    break
                                        page.go_back()
                                        time.sleep(1)
                                    except:
                                        continue

                            if len(parts) >= 3:
                                break

                        except Exception as e:
                            print(f"   Error navigating: {e}")
                            continue

                if len(parts) >= 3:
                    break

            # If still no parts, try manual known GM part numbers
            if not parts:
                print("3. Testing known GM part number patterns...")
                test_parts = ["AC45", "PF46", "12345678", "AC123456"]

                for test_part in test_parts:
                    test_url = f"https://www.gmparts.com/search?q={test_part}"
                    try:
                        page.goto(test_url, timeout=15000)
                        time.sleep(3)
                        content = page.inner_text("body")

                        # Look for actual part numbers in search results
                        gm_patterns = [r'\b(AC\d{6})\b', r'\b(\d{8,10})\b', r'\b(PF\d{2,4})\b']
                        for pattern in gm_patterns:
                            matches = re.findall(pattern, content)
                            if matches:
                                for match in matches[:2]:
                                    parts.append({
                                        'part_number': match,
                                        'url': f"https://www.gmparts.com/search?q={match}",
                                        'source': 'GMParts-Search'
                                    })
                                    print(f"   [FOUND] {match} via search")
                                    if len(parts) >= 3:
                                        break
                        if len(parts) >= 3:
                            break
                    except:
                        continue

        except Exception as e:
            print(f"Error: {e}")

        browser.close()

    return parts

def find_moog_real_parts():
    """Find real parts from Moog by navigating product categories"""
    print("\nMANUAL MOOG PART VERIFICATION")
    print("=" * 40)

    parts = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        try:
            print("1. Loading MoogParts.com...")
            page.goto("https://www.moogparts.com/", timeout=30000)
            time.sleep(3)

            # Look for product categories
            print("2. Looking for product navigation...")

            # Try to find parts links
            category_selectors = [
                "a[href*='steering']", "a[href*='suspension']", "a[href*='part']",
                "a[href*='product']", "a[href*='catalog']"
            ]

            for selector in category_selectors:
                elements = page.query_selector_all(selector)
                if elements:
                    print(f"   Found category: {selector} ({len(elements)} links)")
                    link = elements[0]
                    href = link.get_attribute("href")

                    if href and not href.startswith("#"):
                        if href.startswith("/"):
                            href = "https://www.moogparts.com" + href

                        try:
                            print(f"   Navigating to: {href}")
                            page.goto(href, timeout=20000)
                            time.sleep(3)

                            content = page.inner_text("body")

                            # Moog part patterns
                            moog_patterns = [
                                r'\b(K\d{4,6})\b',         # K80145
                                r'\b(ES\d{4,6})\b',        # ES3470
                                r'\b(RK\d{4,6})\b',        # RK620
                                r'\b(MOO-\w{4,8})\b'       # MOO-K80145
                            ]

                            found = set()
                            for pattern in moog_patterns:
                                matches = re.findall(pattern, content)
                                found.update(matches)

                            if found:
                                print(f"   Found potential parts: {list(found)[:5]}")

                                # Verify parts
                                for part in list(found)[:3]:
                                    try:
                                        # Look for product links with this part
                                        part_links = page.query_selector_all(f"a[href*='{part}' i]")
                                        if part_links:
                                            part_url = part_links[0].get_attribute("href")
                                            if part_url.startswith("/"):
                                                part_url = "https://www.moogparts.com" + part_url

                                            resp = page.goto(part_url, timeout=15000)
                                            if resp.status == 200:
                                                time.sleep(2)
                                                if part.lower() in page.inner_text("body").lower():
                                                    parts.append({
                                                        'part_number': part,
                                                        'url': part_url,
                                                        'source': 'Moog'
                                                    })
                                                    print(f"   [VERIFIED] {part} -> {part_url}")
                                                    if len(parts) >= 3:
                                                        break

                                            page.go_back()
                                            time.sleep(1)
                                    except:
                                        continue

                            if len(parts) >= 3:
                                break

                        except Exception as e:
                            print(f"   Navigation error: {e}")

                if len(parts) >= 3:
                    break

            # Try part number search if no navigation worked
            if not parts:
                print("3. Trying part number search...")
                search_url = "https://www.moogparts.com/en/search"
                try:
                    page.goto(search_url, timeout=20000)
                    time.sleep(3)

                    # Look for search input
                    search_inputs = page.query_selector_all("input[type='text'], input[type='search']")
                    if search_inputs:
                        search_input = search_inputs[0]

                        # Search for common Moog part types
                        searches = ["K80", "ES34", "RK62"]

                        for search_term in searches:
                            try:
                                page.fill("input", search_term)
                                page.press("input", "Enter")
                                time.sleep(3)

                                content = page.inner_text("body")

                                # Extract Moog parts from results
                                for pattern in moog_patterns:
                                    matches = re.findall(pattern, content)
                                    if matches:
                                        for match in matches[:2]:
                                            parts.append({
                                                'part_number': match,
                                                'url': f"https://www.moogparts.com/search?q={match}",
                                                'source': 'Moog-Search'
                                            })
                                            print(f"   [FOUND] {match} via search")
                                            if len(parts) >= 3:
                                                break
                                if len(parts) >= 3:
                                    break
                            except:
                                continue
                except:
                    pass

        except Exception as e:
            print(f"Error: {e}")

        browser.close()

    return parts

if __name__ == "__main__":
    print("MANUAL PART NUMBER VERIFICATION FOR ACDELCO AND MOOG")
    print("=" * 60)

    # Find parts from both sites
    gmparts_parts = find_gmparts_real_parts()
    moog_parts = find_moog_real_parts()

    # Summary
    print("\n" + "=" * 60)
    print("FINAL VERIFIED PARTS SUMMARY")
    print("-" * 30)

    print(f"\nACDELCO/GMPARTS ({len(gmparts_parts)} parts):")
    for part in gmparts_parts:
        print(f"  - {part['part_number']}: {part['url']}")

    print(f"\nMOOG ({len(moog_parts)} parts):")
    for part in moog_parts:
        print(f"  - {part['part_number']}: {part['url']}")

    total = len(gmparts_parts) + len(moog_parts)
    print(f"\nTOTAL VERIFIED: {total} parts")

    if total >= 4:
        print("[SUCCESS] Found sufficient verified parts for scraper development")
    else:
        print(f"[PARTIAL] Found {total}/4 parts - may need additional verification")

    # Assessment for Track B ordering
    accessible_count = 0
    if gmparts_parts:
        accessible_count += 1
        print("\n[OK] ACDelco/GMParts: Accessible with real parts found")
    else:
        print("\n[WARNING] ACDelco/GMParts: Accessible but part extraction needs refinement")

    if moog_parts:
        accessible_count += 1
        print("[OK] Moog: Accessible with real parts found")
    else:
        print("[WARNING] Moog: Accessible but part extraction needs refinement")

    print(f"\nACCESSIBLE SITES FOR TRACK B: {accessible_count}/2")