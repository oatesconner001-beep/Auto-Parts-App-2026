#!/usr/bin/env python3
"""
Simple test of ShowMeTheParts access
"""

from playwright.sync_api import sync_playwright
import time

def test_simple_access():
    """Test simple access to ShowMeTheParts"""
    print("Testing simple ShowMeTheParts access...")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,  # Visible to see what happens
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ]
        )

        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        )

        page = context.new_page()

        # Apply basic stealth
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
        """)

        print("Navigating to ShowMeTheParts...")
        response = page.goto("https://www.showmetheparts.com/", timeout=30000)

        print(f"Initial response status: {response.status}")

        # Wait and see what happens
        print("Waiting 15 seconds to see challenge resolution...")
        time.sleep(15)

        title = page.title()
        url = page.url
        print(f"After wait - Title: {title}")
        print(f"After wait - URL: {url}")

        # Try to get page content
        try:
            body = page.inner_text("body")[:300]
            print(f"Page content preview: {body}")
        except:
            print("Could not get page content")

        # Keep open for manual inspection
        print("Keeping browser open for 30 seconds for inspection...")
        time.sleep(30)

        browser.close()

if __name__ == "__main__":
    test_simple_access()