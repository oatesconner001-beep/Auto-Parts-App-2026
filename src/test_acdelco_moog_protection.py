#!/usr/bin/env python3
"""
Test ACDelco.com and MoogParts.com for bot protection
"""

from playwright.sync_api import sync_playwright
import requests
import time
import re

def test_site_protection(site_name, base_url):
    """Test a site for bot protection"""
    print(f"\n{site_name.upper()} BOT PROTECTION TEST")
    print("=" * 50)

    results = {
        'site_name': site_name,
        'base_url': base_url,
        'http_accessible': False,
        'playwright_accessible': False,
        'protection_type': None,
        'verified_parts': []
    }

    # Step 1: HTTP Test
    print("1. Testing basic HTTP access...")

    try:
        response = requests.get(base_url, timeout=15)
        print(f"   HTTP Status: {response.status_code}")
        print(f"   Content-Type: {response.headers.get('Content-Type', 'N/A')}")
        print(f"   Content Length: {len(response.text)}")

        # Check for protection indicators
        content_lower = response.text.lower()
        protection_checks = [
            ('cloudflare', 'cloudflare' in content_lower),
            ('incapsula', 'incapsula' in content_lower),
            ('shieldsquare', 'shieldsquare' in content_lower),
            ('captcha', 'captcha' in content_lower),
            ('challenge', 'challenge' in content_lower),
            ('access denied', 'access denied' in content_lower),
            ('security check', 'security check' in content_lower),
            ('just a moment', 'just a moment' in content_lower)
        ]

        detected_protection = [name for name, found in protection_checks if found]

        if response.status_code == 403:
            print(f"   [BLOCKED] HTTP 403 - Bot protection active")
            results['protection_type'] = 'HTTP 403 Block'
        elif response.status_code == 200:
            if detected_protection:
                print(f"   [CHALLENGE] Protection detected: {', '.join(detected_protection)}")
                results['protection_type'] = f"Challenge Page ({', '.join(detected_protection)})"
            else:
                print(f"   [OK] HTTP access successful, no protection detected")
                results['http_accessible'] = True
        else:
            print(f"   [WARNING] Unusual status: {response.status_code}")
            results['protection_type'] = f'HTTP {response.status_code}'

    except Exception as e:
        print(f"   [ERROR] HTTP request failed: {e}")
        results['protection_type'] = 'HTTP Request Failed'

    # Step 2: Playwright Test
    print(f"\n2. Testing with Playwright automation...")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)  # Visible to see challenges
            page = browser.new_page()

            print(f"   Loading {site_name} homepage...")
            response = page.goto(base_url, timeout=30000)
            print(f"   Playwright Status: {response.status}")

            # Wait for challenges/redirects
            time.sleep(5)

            # Get page state
            title = page.title()
            url = page.url
            body_text = page.inner_text("body")[:500] if page.query_selector("body") else ""

            print(f"   Page Title: {title}")
            print(f"   Final URL: {url}")
            print(f"   Body preview: {body_text[:100]}...")

            # Check for challenge indicators
            challenge_indicators = [
                'checking your browser',
                'please wait',
                'verify you are human',
                'captcha',
                'challenge',
                'access denied',
                'security verification',
                'blocked',
                'just a moment'
            ]

            challenge_detected = any(indicator in body_text.lower() for indicator in challenge_indicators)

            if challenge_detected:
                print(f"   [CHALLENGE] Challenge page detected")
                challenge_types = [ind for ind in challenge_indicators if ind in body_text.lower()]
                results['protection_type'] = f"Challenge: {', '.join(challenge_types)}"
            elif response.status == 403:
                print(f"   [BLOCKED] Playwright also blocked (403)")
                results['protection_type'] = 'Playwright 403 Block'
            elif len(body_text) > 200:
                print(f"   [OK] Normal content loaded")
                results['playwright_accessible'] = True

                # Try to find parts if accessible
                print(f"   Attempting to find part numbers...")
                found_parts = extract_parts_from_page(page, site_name)
                results['verified_parts'] = found_parts

            browser.close()

    except Exception as e:
        print(f"   [ERROR] Playwright test failed: {e}")
        if 'protection_type' not in results or not results['protection_type']:
            results['protection_type'] = f'Playwright Error: {str(e)[:50]}'

    return results

def extract_parts_from_page(page, site_name):
    """Extract part numbers from accessible page"""
    try:
        # Get page content
        page_text = page.inner_text("body")

        # Look for part number patterns common to auto parts
        patterns = [
            r'\b([A-Z]{2,4}\d{4,8})\b',        # AC123456, MOOG12345
            r'\b(\d{2,4}-\d{3,6})\b',          # 12-34567
            r'\b([A-Z]{1,3}\d{2,3}-\d{3,6})\b' # AC12-34567
        ]

        found_parts = set()
        for pattern in patterns:
            matches = re.findall(pattern, page_text)
            found_parts.update(matches)

        # Limit and verify parts exist
        potential_parts = list(found_parts)[:10]
        verified_parts = []

        for part in potential_parts:
            # Try to find links or product pages for this part
            try:
                # Look for links containing this part number
                links = page.query_selector_all(f"a[href*='{part}']")
                if links:
                    link_url = links[0].get_attribute("href")
                    if link_url:
                        if link_url.startswith('/'):
                            link_url = page.url.split('/')[0] + '//' + page.url.split('/')[2] + link_url

                        verified_parts.append({
                            'part_number': part,
                            'url': link_url
                        })

                        if len(verified_parts) >= 3:
                            break

            except:
                continue

        print(f"     Found {len(verified_parts)} potential parts: {[p['part_number'] for p in verified_parts]}")
        return verified_parts

    except Exception as e:
        print(f"     Error extracting parts: {e}")
        return []

if __name__ == "__main__":
    print("TESTING ACDELCO AND MOOG FOR BOT PROTECTION")
    print("=" * 60)

    # Test both sites
    sites_to_test = [
        ('ACDelco', 'https://www.acdelco.com/'),
        ('Moog', 'https://www.moogparts.com/')
    ]

    results = []

    for site_name, url in sites_to_test:
        result = test_site_protection(site_name, url)
        results.append(result)

    # Summary Report
    print(f"\n" + "=" * 60)
    print("COMPLETE BOT PROTECTION ASSESSMENT:")
    print("-" * 45)

    for result in results:
        print(f"\n{result['site_name'].upper()}:")
        print(f"  HTTP Accessible: {result['http_accessible']}")
        print(f"  Playwright Accessible: {result['playwright_accessible']}")
        print(f"  Protection Type: {result['protection_type']}")
        print(f"  Verified Parts Found: {len(result['verified_parts'])}")

        if result['verified_parts']:
            for part in result['verified_parts']:
                print(f"    - {part['part_number']}: {part['url']}")

    # Overall assessment
    accessible_sites = [r for r in results if r['playwright_accessible']]
    protected_sites = [r for r in results if not r['playwright_accessible']]

    print(f"\n" + "=" * 60)
    print("OVERALL TRACK B ASSESSMENT:")
    print(f"Accessible Sites: {len(accessible_sites)}/{len(results)}")
    print(f"Protected Sites: {len(protected_sites)}/{len(results)}")

    if len(accessible_sites) == 0:
        print("\n[CRITICAL] ALL tested sites have bot protection!")
        print("Sites tested with protection:")
        print("  - ShowMeTheParts: Incapsula WAF")
        print("  - Dorman: ShieldSquare")
        print("  - PartsGeek: Cloudflare")
        for result in results:
            print(f"  - {result['site_name']}: {result['protection_type']}")
        print("\nRECOMMENDATION: Build shared stealth_base.py module first")

    elif len(accessible_sites) < len(results):
        print(f"\n[MIXED] {len(accessible_sites)} sites accessible, {len(protected_sites)} protected")
        print("Can implement accessible sites first, then add stealth for protected sites")

    else:
        print(f"\n[SUCCESS] All sites accessible - can use standard scraping")

    print(f"\nTotal sites tested across all sessions: 5")
    print(f"Protection pattern: {4 + len(protected_sites)} out of {4 + len(results)} sites protected")