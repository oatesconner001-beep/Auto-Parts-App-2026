#!/usr/bin/env python3
"""
Test PartsGeek.com for bot protection before scraper development
"""

from playwright.sync_api import sync_playwright
import requests
import time

def test_partsgeek_bot_protection():
    """Test if PartsGeek has bot protection"""
    print("PARTSGEEK BOT PROTECTION TEST")
    print("=" * 40)

    # Step 1: Test with basic HTTP request
    print("1. Testing basic HTTP access...")

    try:
        response = requests.get("https://www.partsgeek.com/", timeout=15)
        print(f"   HTTP Status: {response.status_code}")
        print(f"   Content-Type: {response.headers.get('Content-Type', 'N/A')}")
        print(f"   Content Length: {len(response.text)}")

        # Check for bot protection indicators
        content_lower = response.text.lower()
        protection_indicators = [
            ('cloudflare', 'cloudflare' in content_lower),
            ('incapsula', 'incapsula' in content_lower),
            ('shieldsquare', 'shieldsquare' in content_lower),
            ('captcha', 'captcha' in content_lower),
            ('challenge', 'challenge' in content_lower),
            ('access_denied', 'access denied' in content_lower)
        ]

        protection_found = []
        for name, found in protection_indicators:
            if found:
                protection_found.append(name)

        if protection_found:
            print(f"   [WARNING] Potential protection detected: {', '.join(protection_found)}")
        else:
            print(f"   [OK] No obvious protection indicators in HTTP response")

        # Check if we got actual content
        if response.status_code == 200 and len(response.text) > 1000:
            print(f"   [OK] Got substantial content ({len(response.text)} chars)")
        elif response.status_code == 403:
            print(f"   [ERROR] HTTP 403 - Bot protection likely active")
            return False
        else:
            print(f"   [WARNING] Minimal content or unusual status")

    except Exception as e:
        print(f"   [ERROR] HTTP request failed: {e}")
        return False

    # Step 2: Test with Playwright (standard automation)
    print(f"\n2. Testing with Playwright automation...")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()

            print("   Loading PartsGeek homepage...")
            response = page.goto("https://www.partsgeek.com/", timeout=30000)

            print(f"   Playwright Status: {response.status}")

            # Wait a moment for any challenges to appear
            time.sleep(5)

            # Get page content
            title = page.title()
            url = page.url

            print(f"   Page Title: {title}")
            print(f"   Final URL: {url}")

            # Check for challenge indicators
            body_text = page.inner_text("body")[:500] if page.query_selector("body") else ""
            print(f"   Body preview: {body_text[:100]}...")

            challenge_indicators = [
                'checking your browser',
                'please wait',
                'verify you are human',
                'captcha',
                'challenge',
                'access denied',
                'blocked'
            ]

            challenge_detected = any(indicator in body_text.lower() for indicator in challenge_indicators)

            if challenge_detected:
                print(f"   [WARNING] Challenge page detected in Playwright")
                return False
            elif len(body_text) < 100:
                print(f"   [WARNING] Very little content loaded")
                return False
            else:
                print(f"   [OK] Normal page content loaded")

            browser.close()
            return True

    except Exception as e:
        print(f"   [ERROR] Playwright test failed: {e}")
        return False

def test_partsgeek_product_page():
    """Test a known product page format"""
    print(f"\n3. Testing product page access...")

    # Try some common product page patterns
    test_urls = [
        "https://www.partsgeek.com/mmercedes-benz-c230/oil_filter.html",
        "https://www.partsgeek.com/gbmw/brake_pads.html",
        "https://www.partsgeek.com/catalog/search.php?q=oil+filter"
    ]

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)  # Visible to see what happens
            page = browser.new_page()

            for test_url in test_urls:
                print(f"   Testing: {test_url}")

                try:
                    response = page.goto(test_url, timeout=20000)
                    print(f"     Status: {response.status}")

                    time.sleep(3)

                    title = page.title()
                    body_preview = page.inner_text("body")[:200] if page.query_selector("body") else ""

                    print(f"     Title: {title}")
                    print(f"     Content: {body_preview[:80]}...")

                    if response.status == 200 and len(body_preview) > 50:
                        print(f"     [OK] Product page accessible")
                        browser.close()
                        return True
                    else:
                        print(f"     [WARNING] Limited content")

                except Exception as e:
                    print(f"     [ERROR] {e}")

            browser.close()

    except Exception as e:
        print(f"   [ERROR] Product page test failed: {e}")

    return False

if __name__ == "__main__":
    print("Testing PartsGeek.com for bot protection...")
    print("This will determine if we need stealth techniques or can use standard scraping.")
    print()

    # Run all tests
    http_ok = test_partsgeek_bot_protection()
    product_ok = test_partsgeek_product_page()

    print(f"\n" + "=" * 40)
    print("PARTSGEEK BOT PROTECTION TEST RESULTS:")
    print("-" * 45)

    if http_ok and product_ok:
        print("[SUCCESS] PartsGeek appears to allow standard scraping")
        print("No bot protection detected - can proceed with normal Playwright scraper")
    elif http_ok:
        print("[PARTIAL] Basic access works but product pages may have issues")
        print("May need light stealth techniques")
    else:
        print("[BLOCKED] PartsGeek has bot protection")
        print("Will need stealth techniques similar to Dorman/ShowMeTheParts")

    print(f"\nHTTP Test: {'PASS' if http_ok else 'FAIL'}")
    print(f"Product Test: {'PASS' if product_ok else 'FAIL'}")

    if not (http_ok and product_ok):
        print(f"\n[ALERT] PartsGeek protection detected - need to reassess Track B order")
    else:
        print(f"\n[OK] Ready to find real PartsGeek part numbers for testing")