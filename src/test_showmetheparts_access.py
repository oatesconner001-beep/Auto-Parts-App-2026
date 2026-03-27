#!/usr/bin/env python3
"""
Test ShowMeTheParts access to identify actual blocking mechanism
"""

import requests
import time
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth

def test_basic_http_access():
    """Test basic HTTP access"""
    print("1. TESTING BASIC HTTP ACCESS")
    print("-" * 40)

    try:
        # Test with basic requests
        response = requests.get("https://www.showmetheparts.com/", timeout=10)
        print(f"Basic HTTP status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        if response.status_code != 200:
            print(f"Response text: {response.text[:500]}")
    except Exception as e:
        print(f"Basic HTTP failed: {e}")

def test_browser_headers_access():
    """Test with proper browser headers"""
    print("\n2. TESTING WITH BROWSER HEADERS")
    print("-" * 40)

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'sec-ch-ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"'
    }

    try:
        response = requests.get("https://www.showmetheparts.com/",
                              headers=headers, timeout=10)
        print(f"Browser headers status: {response.status_code}")
        if response.status_code == 403:
            print("DETECTED: 403 Forbidden with browser headers")
            print(f"Response text: {response.text[:500]}")
            if 'cloudflare' in response.text.lower():
                print("IDENTIFIED: Cloudflare protection")
            elif 'incapsula' in response.text.lower():
                print("IDENTIFIED: Incapsula protection")
            elif 'access denied' in response.text.lower():
                print("IDENTIFIED: Generic access denied")
    except Exception as e:
        print(f"Browser headers failed: {e}")

def test_playwright_basic():
    """Test with basic Playwright"""
    print("\n3. TESTING PLAYWRIGHT BASIC")
    print("-" * 40)

    try:
        with sync_playwright() as p:
            # Use real Chrome instead of Chromium
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-web-security",
                ]
            )
            page = browser.new_page()

            response = page.goto("https://www.showmetheparts.com/", timeout=30000)
            status = response.status if response else "no response"
            print(f"Playwright basic status: {status}")

            if status == 403:
                body_text = page.inner_text("body")[:500]
                print(f"403 response body: {body_text}")

            browser.close()

    except Exception as e:
        print(f"Playwright basic failed: {e}")

def test_playwright_stealth():
    """Test with Playwright + stealth"""
    print("\n4. TESTING PLAYWRIGHT + STEALTH")
    print("-" * 40)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-web-security",
                    "--no-sandbox",
                    "--disable-features=TranslateUI",
                    "--disable-ipc-flooding-protection",
                ]
            )

            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                viewport={"width": 1366, "height": 768},
                extra_http_headers={
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept-Encoding": "gzip, deflate, br",
                    "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
                    "sec-ch-ua-mobile": "?0",
                    "sec-ch-ua-platform": '"Windows"',
                    "Sec-Fetch-Dest": "document",
                    "Sec-Fetch-Mode": "navigate",
                    "Sec-Fetch-Site": "none",
                    "Sec-Fetch-User": "?1",
                    "Upgrade-Insecure-Requests": "1",
                }
            )

            page = context.new_page()

            # Apply stealth patches
            stealth(page)

            # Override webdriver property
            page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
            """)

            response = page.goto("https://www.showmetheparts.com/", timeout=30000)
            status = response.status if response else "no response"
            print(f"Playwright + stealth status: {status}")

            if status == 200:
                print("SUCCESS: Stealth access working!")
                title = page.title()
                print(f"Page title: {title}")

                # Test search functionality
                print("\nTesting search functionality...")
                time.sleep(2)

                search_response = page.goto("https://www.showmetheparts.com/anchor/search?searchterm=3217",
                                           timeout=30000)
                search_status = search_response.status if search_response else "no response"
                print(f"Search page status: {search_status}")

                if search_status == 200:
                    search_title = page.title()
                    print(f"Search page title: {search_title}")
                    body_preview = page.inner_text("body")[:300]
                    print(f"Search page preview: {body_preview}")

            elif status == 403:
                body_text = page.inner_text("body")[:500]
                print(f"403 response body: {body_text}")

            browser.close()

    except Exception as e:
        print(f"Playwright stealth failed: {e}")

def test_session_warmup():
    """Test with session warmup approach"""
    print("\n5. TESTING SESSION WARMUP APPROACH")
    print("-" * 40)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=False,  # Make visible to see what's happening
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-web-security",
                    "--no-sandbox",
                ]
            )

            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                viewport={"width": 1366, "height": 768}
            )

            page = context.new_page()
            stealth(page)

            # Step 1: Visit homepage and establish session
            print("Step 1: Visiting homepage...")
            home_response = page.goto("https://www.showmetheparts.com/", timeout=30000)
            home_status = home_response.status if home_response else "no response"
            print(f"Homepage status: {home_status}")

            if home_status == 200:
                print("Waiting to establish session...")
                time.sleep(3)

                # Step 2: Navigate to specific brand page
                print("Step 2: Visiting Anchor brand page...")
                brand_response = page.goto("https://www.showmetheparts.com/anchor/", timeout=30000)
                brand_status = brand_response.status if brand_response else "no response"
                print(f"Brand page status: {brand_status}")

                if brand_status == 200:
                    time.sleep(2)

                    # Step 3: Try search
                    print("Step 3: Testing search...")
                    search_response = page.goto("https://www.showmetheparts.com/anchor/search?searchterm=3217",
                                               timeout=30000)
                    search_status = search_response.status if search_response else "no response"
                    print(f"Search status: {search_status}")

                    if search_status == 200:
                        print("SUCCESS: Full session warmup working!")
                        search_content = page.inner_text("body")[:500]
                        print(f"Search content preview: {search_content}")

            print("Keeping browser open for 10 seconds for manual inspection...")
            time.sleep(10)
            browser.close()

    except Exception as e:
        print(f"Session warmup failed: {e}")

if __name__ == "__main__":
    print("SHOWMETHEPARTS ACCESS INVESTIGATION")
    print("=" * 50)

    test_basic_http_access()
    test_browser_headers_access()
    test_playwright_basic()
    test_playwright_stealth()
    test_session_warmup()

    print("\n" + "=" * 50)
    print("INVESTIGATION COMPLETE")