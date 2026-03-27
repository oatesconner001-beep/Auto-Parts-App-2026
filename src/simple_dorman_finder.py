#!/usr/bin/env python3
"""
Simple direct approach to find real Dorman parts
"""

from playwright.sync_api import sync_playwright
import time
import requests

def find_dorman_parts_simple():
    """Try direct HTTP approach first, then browser if needed"""
    print("DIRECT DORMAN PARTS VERIFICATION")
    print("=" * 40)

    # Try accessing Dorman's sitemap or product listing directly
    base_urls_to_try = [
        "https://www.dormanproducts.com/sitemap.xml",
        "https://www.dormanproducts.com/sitemap/",
        "https://www.dormanproducts.com/products/",
        "https://www.dormanproducts.com/catalog/",
        "https://www.dormanproducts.com/gsearch.aspx?keyword=door"
    ]

    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })

    found_parts = []

    for url in base_urls_to_try:
        try:
            print(f"\nTrying: {url}")
            response = session.get(url, timeout=15)
            print(f"Status: {response.status_code}")

            if response.status_code == 200:
                content = response.text
                print(f"Content length: {len(content)} characters")

                # Look for Dorman part number patterns
                import re
                patterns = [
                    r'\b(\d{3}-\d{3})\b',  # 924-503 format
                    r'\b(\d{3}-\d{4})\b',  # 924-5037 format
                ]

                for pattern in patterns:
                    matches = re.findall(pattern, content)
                    if matches:
                        unique_matches = list(set(matches))[:10]
                        print(f"Found pattern {pattern}: {len(unique_matches)} parts")

                        for part in unique_matches[:3]:
                            # Try to verify this part has a real page
                            test_url = f"https://www.dormanproducts.com/p-{part}.aspx"
                            try:
                                test_response = session.get(test_url, timeout=10)
                                if test_response.status_code == 200 and part in test_response.text:
                                    found_parts.append({
                                        'part_number': part,
                                        'url': test_url,
                                        'verified': True
                                    })
                                    print(f"  VERIFIED: {part} -> {test_url}")
                            except:
                                pass

                if found_parts and len(found_parts) >= 3:
                    break

        except Exception as e:
            print(f"Error with {url}: {e}")

    # If we still don't have enough, try browser approach with shorter timeout
    if len(found_parts) < 3:
        print("\nTrying browser approach with reduced timeouts...")
        browser_parts = find_with_browser()
        found_parts.extend(browser_parts)

    return found_parts

def find_with_browser():
    """Browser approach with shorter timeouts"""
    parts = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            page = browser.new_page()

            # Go to Dorman with shorter timeout
            page.goto("https://www.dormanproducts.com/", timeout=20000)

            # Don't wait for networkidle, just give it a few seconds
            time.sleep(5)

            print("Checking for search or navigation elements...")

            # Look for any links that might contain part numbers
            all_links = page.query_selector_all("a[href]")

            for link in all_links[:50]:  # Check first 50 links
                try:
                    href = link.get_attribute("href")
                    text = link.inner_text()

                    # Look for part number patterns in links
                    import re
                    if re.search(r'\d{3}-\d{3,4}', href + " " + text):
                        part_matches = re.findall(r'(\d{3}-\d{3,4})', href + " " + text)
                        if part_matches:
                            for part in part_matches[:2]:
                                if href.startswith('/'):
                                    full_url = "https://www.dormanproducts.com" + href
                                else:
                                    full_url = href

                                parts.append({
                                    'part_number': part,
                                    'url': full_url,
                                    'verified': False
                                })

                                if len(parts) >= 5:
                                    break

                    if len(parts) >= 5:
                        break

                except:
                    continue

            browser.close()

    except Exception as e:
        print(f"Browser error: {e}")

    return parts

if __name__ == "__main__":
    parts = find_dorman_parts_simple()

    print("\n" + "=" * 40)
    print("FOUND DORMAN PARTS:")
    print("-" * 25)

    if parts:
        for i, part in enumerate(parts[:5], 1):
            status = "VERIFIED" if part.get('verified') else "FOUND"
            print(f"{i}. {part['part_number']} - {status}")
            print(f"   URL: {part['url']}")
    else:
        print("No parts found - manual investigation required")

    print(f"\nTotal found: {len(parts)}")