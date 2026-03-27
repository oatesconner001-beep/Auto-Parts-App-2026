#!/usr/bin/env python3
"""
Manual check of common Dorman part numbers
"""

import requests

def check_dorman_parts_manually():
    """Manually check known Dorman part patterns"""
    print("MANUAL VERIFICATION OF DORMAN PARTS")
    print("=" * 40)

    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    })

    # Test common Dorman part number ranges
    test_parts = [
        # Already verified
        "800-523",
        "523-2492",
        # New tests - different number ranges
        "924-5108",  # Window regulator range
        "924-5109",
        "924-5110",
        "697-364",   # Power steering range
        "697-365",
        "697-366",
        "620-281",   # Radiator range
        "620-282",
        "620-283",
        "746-616",   # Door handle range
        "746-617",
        "746-618",
        "917-310",   # OE Solutions range
        "917-311",
        "917-312"
    ]

    verified = []

    for part in test_parts:
        url = f"https://www.dormanproducts.com/p-{part}.aspx"

        try:
            response = session.get(url, timeout=10)
            status = response.status_code

            if status == 200:
                # Check if it's actually a product page
                content = response.text.lower()

                if (part in content and
                    any(word in content for word in ['product', 'part', 'specification', 'description', 'vehicle'])):

                    verified.append({
                        'part_number': part,
                        'url': url,
                        'status': 'VERIFIED'
                    })
                    print(f"✓ VERIFIED: {part} -> {url}")
                else:
                    print(f"- Page exists but no product content: {part}")
            elif status == 404:
                print(f"✗ Not found: {part}")
            else:
                print(f"? HTTP {status}: {part}")

        except Exception as e:
            print(f"! Error checking {part}: {e}")

    return verified

if __name__ == "__main__":
    verified_parts = check_dorman_parts_manually()

    print("\n" + "=" * 40)
    print("FINAL VERIFIED DORMAN PARTS FOR TESTING:")
    print("-" * 45)

    if len(verified_parts) >= 5:
        final_parts = verified_parts[:5]
        for i, part in enumerate(final_parts, 1):
            print(f"{i}. {part['part_number']}")
            print(f"   URL: {part['url']}")
            print(f"   Status: {part['status']}")
            print()

        print("✓ SUCCESS: Have 5 verified parts for scraper testing!")

    else:
        print(f"Found {len(verified_parts)} verified parts:")
        for part in verified_parts:
            print(f"  - {part['part_number']}: {part['url']}")
        print(f"\nNeed {5 - len(verified_parts)} more parts")