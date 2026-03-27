#!/usr/bin/env python3
"""
Get more verified Dorman parts through search
"""

import requests
import re

def find_more_dorman_parts():
    """Find more Dorman parts through search"""
    print("FINDING MORE VERIFIED DORMAN PARTS")
    print("=" * 40)

    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })

    # Start with the 2 we already found
    verified_parts = [
        {'part_number': '800-523', 'url': 'https://www.dormanproducts.com/p-800-523.aspx'},
        {'part_number': '523-2492', 'url': 'https://www.dormanproducts.com/p-523-2492.aspx'}
    ]

    # Try search URLs for common parts
    search_terms = [
        "door+handle",
        "window+regulator",
        "control+arm",
        "ball+joint",
        "tie+rod"
    ]

    for term in search_terms:
        search_url = f"https://www.dormanproducts.com/gsearch.aspx?keyword={term}"
        print(f"\nSearching: {term}")

        try:
            response = session.get(search_url, timeout=15)
            print(f"Status: {response.status_code}")

            if response.status_code == 200:
                content = response.text

                # Look for part number patterns in search results
                patterns = [
                    r'\b(\d{3}-\d{3})\b',
                    r'\b(\d{3}-\d{4})\b',
                    r'\b(\d{2,3}-\d{4,5})\b'
                ]

                found_in_search = set()
                for pattern in patterns:
                    matches = re.findall(pattern, content)
                    found_in_search.update(matches)

                print(f"Found {len(found_in_search)} potential parts: {list(found_in_search)[:5]}")

                # Verify each part
                for part in list(found_in_search)[:3]:  # Test first 3
                    if part in [p['part_number'] for p in verified_parts]:
                        continue  # Skip duplicates

                    test_url = f"https://www.dormanproducts.com/p-{part}.aspx"
                    try:
                        test_response = session.get(test_url, timeout=10)
                        if test_response.status_code == 200 and part in test_response.text:
                            verified_parts.append({
                                'part_number': part,
                                'url': test_url
                            })
                            print(f"  VERIFIED: {part}")

                            if len(verified_parts) >= 5:
                                break
                    except:
                        print(f"  Failed to verify: {part}")

                if len(verified_parts) >= 5:
                    break

        except Exception as e:
            print(f"Error searching {term}: {e}")

    return verified_parts[:5]

if __name__ == "__main__":
    parts = find_more_dorman_parts()

    print("\n" + "=" * 40)
    print("FINAL VERIFIED DORMAN PARTS:")
    print("-" * 30)

    for i, part in enumerate(parts, 1):
        print(f"{i}. {part['part_number']}")
        print(f"   URL: {part['url']}")
        print()

    print(f"Total verified parts: {len(parts)}")

    if len(parts) >= 5:
        print("SUCCESS: Ready for Dorman scraper development!")
    else:
        print(f"Need {5 - len(parts)} more verified parts")