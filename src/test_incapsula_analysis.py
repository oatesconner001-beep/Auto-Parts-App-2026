#!/usr/bin/env python3
"""
Analysis of Incapsula protection on ShowMeTheParts
"""

import requests
import time
from playwright.sync_api import sync_playwright

def analyze_incapsula_response():
    """Analyze the Incapsula response in detail"""
    print("INCAPSULA PROTECTION ANALYSIS")
    print("=" * 40)

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
    }

    try:
        response = requests.get("https://www.showmetheparts.com/", headers=headers, timeout=10)

        print(f"Status Code: {response.status_code}")
        print(f"Content-Type: {response.headers.get('Content-Type')}")
        print(f"Content-Length: {response.headers.get('Content-Length')}")

        # Look for Incapsula signatures
        incap_headers = {k: v for k, v in response.headers.items() if 'incap' in k.lower()}
        print(f"Incapsula Headers: {incap_headers}")

        print(f"\nFull Response Text:")
        print("-" * 20)
        print(response.text)

        # Check if this is a JavaScript challenge page
        if "/_Incapsula_Resource" in response.text:
            print("\nDETECTED: Incapsula JavaScript Challenge")
            print("This requires JavaScript execution to complete")

        return response.text

    except Exception as e:
        print(f"Request failed: {e}")
        return None

def test_playwright_stealth_corrected():
    """Test Playwright with corrected stealth setup"""
    print("\nPLAYWRIGHT + STEALTH TEST (CORRECTED)")
    print("=" * 40)

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=False,  # Make visible to see challenge
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-web-security",
                    "--no-sandbox",
                    "--disable-features=TranslateUI",
                    "--disable-dev-shm-usage",
                    "--disable-extensions",
                    "--no-first-run",
                    "--disable-default-apps",
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

            # Apply stealth manually instead of using the module
            page.add_init_script("""
                // Remove webdriver property
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });

                // Mock plugins
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });

                // Mock languages
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en'],
                });

                // Override permissions
                const originalQuery = window.navigator.permissions.query;
                window.navigator.permissions.query = (parameters) => (
                    parameters.name === 'notifications' ?
                        Promise.resolve({ state: Notification.permission }) :
                        originalQuery(parameters)
                );
            """)

            print("Navigating to ShowMeTheParts...")
            response = page.goto("https://www.showmetheparts.com/", timeout=30000)
            status = response.status if response else "no response"
            print(f"Initial response status: {status}")

            if status == 403:
                print("Got 403, waiting for potential JavaScript challenge resolution...")
                # Wait for potential challenge to complete
                time.sleep(10)

                # Check if page content changed
                title = page.title()
                print(f"Page title after wait: {title}")

                url = page.url
                print(f"Current URL: {url}")

                # Take screenshot for analysis
                page.screenshot(path="showmetheparts_challenge.png")
                print("Screenshot saved as 'showmetheparts_challenge.png'")

                # Get page content
                body_text = page.inner_text("body")[:1000]
                print(f"Page content preview: {body_text}")

            elif status == 200:
                print("SUCCESS: Access granted!")
                title = page.title()
                print(f"Page title: {title}")

            # Keep browser open for manual inspection
            print("Keeping browser open for 15 seconds for manual inspection...")
            time.sleep(15)

            browser.close()

    except Exception as e:
        print(f"Playwright stealth test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    analyze_incapsula_response()
    test_playwright_stealth_corrected()