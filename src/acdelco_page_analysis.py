#!/usr/bin/env python3
"""
Pre-code analysis of ACDelco/GMParts product page structure
Analyze one of the 5 verified parts to understand page layout before scraper development
"""

from playwright.sync_api import sync_playwright
import time
import json

def analyze_acdelco_product_page():
    """Analyze ACDelco product page structure for parsing approach"""

    # Use first verified part from our findings
    test_part = "12735811"
    print(f"ACDELCO PRODUCT PAGE ANALYSIS")
    print(f"Analyzing GM Part: {test_part}")
    print("=" * 50)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        try:
            # Try common GM/ACDelco product page URL patterns
            test_urls = [
                f"https://www.gmparts.com/p-{test_part}.aspx",
                f"https://parts.gmparts.com/part/{test_part}",
                f"https://www.gmparts.com/search?q={test_part}",
                f"https://parts.gmparts.com/search?q={test_part}"
            ]

            found_product_page = False

            for url in test_urls:
                print(f"\n1. TESTING URL: {url}")

                try:
                    response = page.goto(url, timeout=20000)
                    print(f"   Status: {response.status}")

                    if response.status == 200:
                        time.sleep(3)

                        page_title = page.title()
                        page_url = page.url
                        print(f"   Title: {page_title}")
                        print(f"   Final URL: {page_url}")

                        # Check if this contains our part number
                        body_text = page.inner_text("body").lower()
                        if test_part.lower() in body_text:
                            print(f"   [SUCCESS] Found part {test_part} on page!")
                            found_product_page = True

                            # Analyze page structure
                            print(f"\n2. PAGE STRUCTURE ANALYSIS:")
                            analyze_page_structure(page, test_part)
                            break
                        else:
                            print(f"   [INFO] Page loaded but part {test_part} not found in content")

                except Exception as e:
                    print(f"   [ERROR] Failed to load {url}: {e}")
                    continue

            if not found_product_page:
                print(f"\n[FALLBACK] Direct product page not found, trying search approach...")
                search_for_part(page, test_part)

        except Exception as e:
            print(f"Error in analysis: {e}")

        browser.close()

def analyze_page_structure(page, part_number):
    """Analyze the structure of a confirmed product page"""

    try:
        # Extract key page elements
        print(f"   Analyzing page elements for part {part_number}...")

        # 1. Part Number Location
        print(f"\n   A. PART NUMBER IDENTIFICATION:")
        part_selectors = [
            f"*:contains('{part_number}')",
            ".part-number", ".partnum", "#partNumber",
            ".product-id", ".item-number"
        ]

        part_elements = []
        for selector in part_selectors:
            try:
                if selector.startswith("*:contains"):
                    # Use text search
                    elements = page.query_selector_all(f"text={part_number}")
                else:
                    elements = page.query_selector_all(selector)

                if elements:
                    for elem in elements[:2]:  # Limit to first 2
                        text = elem.inner_text()[:100]
                        tag = elem.evaluate("el => el.tagName")
                        part_elements.append(f"{tag}: {text}")
            except:
                continue

        if part_elements:
            print(f"      Found part number in: {part_elements}")
        else:
            print(f"      Part number location: Need to identify")

        # 2. Product Name/Description
        print(f"\n   B. PRODUCT NAME/DESCRIPTION:")
        name_selectors = [
            "h1", ".product-name", ".part-name", ".title",
            ".product-title", ".description h1", ".product-description h1"
        ]

        for selector in name_selectors:
            try:
                element = page.query_selector(selector)
                if element:
                    text = element.inner_text().strip()
                    if text and len(text) > 5:  # Valid product name
                        print(f"      {selector}: {text[:100]}")
                        break
            except:
                continue

        # 3. Brand Information
        print(f"\n   C. BRAND IDENTIFICATION:")
        brand_selectors = [
            ".brand", ".manufacturer", ".product-brand",
            "*:contains('ACDelco')", "*:contains('GM Genuine')",
            "*:contains('General Motors')"
        ]

        brand_found = False
        for selector in brand_selectors:
            try:
                if "*:contains" in selector:
                    brand_text = selector.split("'")[1]
                    if brand_text.lower() in page.inner_text("body").lower():
                        print(f"      Found brand reference: {brand_text}")
                        brand_found = True
                else:
                    element = page.query_selector(selector)
                    if element:
                        text = element.inner_text().strip()
                        print(f"      {selector}: {text}")
                        brand_found = True
            except:
                continue

        if not brand_found:
            print(f"      Brand identification: Need manual detection")

        # 4. Price Information
        print(f"\n   D. PRICE INFORMATION:")
        price_selectors = [
            ".price", ".cost", ".msrp", ".retail-price",
            ".product-price", "*[class*='price']", "*[id*='price']"
        ]

        for selector in price_selectors:
            try:
                elements = page.query_selector_all(selector)
                for elem in elements:
                    text = elem.inner_text().strip()
                    if "$" in text or "price" in text.lower():
                        print(f"      {selector}: {text}")
                        break
            except:
                continue

        # 5. CRITICAL: Fitment Data Analysis
        print(f"\n   E. FITMENT DATA (CRITICAL - TABLE HAS 0 ROWS):")
        fitment_selectors = [
            ".fitment", ".compatibility", ".vehicle-fit",
            ".applications", ".fits", "table", ".year-make-model",
            ".vehicle-table", ".application-table"
        ]

        fitment_found = False
        for selector in fitment_selectors:
            try:
                elements = page.query_selector_all(selector)
                for elem in elements:
                    text = elem.inner_text().strip().lower()
                    if any(keyword in text for keyword in ['year', 'make', 'model', 'engine', 'fitment', 'fits']):
                        print(f"      FITMENT FOUND - {selector}: {text[:200]}")
                        fitment_found = True

                        # Check if it's a table with rows
                        if elem.query_selector("tr"):
                            rows = elem.query_selector_all("tr")
                            print(f"      --> Table with {len(rows)} rows")
                            if len(rows) > 1:  # Header + data rows
                                # Show first data row as example
                                first_row = rows[1].inner_text() if len(rows) > 1 else rows[0].inner_text()
                                print(f"      --> Sample row: {first_row}")
                        break
            except:
                continue

        if not fitment_found:
            print(f"      [CRITICAL] No fitment data found - need alternative approach")

        # 6. OEM Cross-References
        print(f"\n   F. OEM CROSS-REFERENCES:")
        oem_selectors = [
            ".oem", ".cross-reference", ".part-cross-ref",
            ".alternate-parts", ".superseded", ".replaces",
            "*:contains('OEM')", "*:contains('Original Equipment')"
        ]

        oem_found = False
        for selector in oem_selectors:
            try:
                if "*:contains" in selector:
                    search_term = selector.split("'")[1]
                    body_text = page.inner_text("body")
                    if search_term.lower() in body_text.lower():
                        print(f"      Found OEM reference: Contains '{search_term}'")
                        oem_found = True
                else:
                    elements = page.query_selector_all(selector)
                    for elem in elements:
                        text = elem.inner_text().strip()
                        if text and len(text) > 3:
                            print(f"      {selector}: {text[:100]}")
                            oem_found = True
                            break
            except:
                continue

        if not oem_found:
            print(f"      OEM cross-references: Need to identify")

        # 7. Technical Specifications
        print(f"\n   G. TECHNICAL SPECIFICATIONS:")
        spec_selectors = [
            ".specs", ".specifications", ".technical-data",
            ".product-specs", ".details", ".attributes",
            ".features", ".properties"
        ]

        for selector in spec_selectors:
            try:
                elements = page.query_selector_all(selector)
                for elem in elements:
                    text = elem.inner_text().strip()
                    if text and len(text) > 10:
                        print(f"      {selector}: {text[:100]}...")
                        break
            except:
                continue

        # 8. Product Images
        print(f"\n   H. PRODUCT IMAGES:")
        image_selectors = [
            ".product-image img", ".part-image img", ".main-image img",
            "img[src*='part']", "img[src*='product']", ".gallery img"
        ]

        for selector in image_selectors:
            try:
                images = page.query_selector_all(selector)
                for img in images:
                    src = img.get_attribute("src")
                    alt = img.get_attribute("alt")
                    if src:
                        print(f"      {selector}: {src}")
                        if alt:
                            print(f"        Alt text: {alt}")
                        break
            except:
                continue

        # 9. Availability/Stock
        print(f"\n   I. AVAILABILITY/STOCK STATUS:")
        stock_selectors = [
            ".availability", ".stock", ".in-stock", ".out-of-stock",
            ".inventory", ".qty", "*:contains('Available')",
            "*:contains('In Stock')", "*:contains('Out of Stock')"
        ]

        for selector in stock_selectors:
            try:
                if "*:contains" in selector:
                    search_term = selector.split("'")[1]
                    if search_term.lower() in page.inner_text("body").lower():
                        print(f"      Found availability text: '{search_term}'")
                else:
                    elements = page.query_selector_all(selector)
                    for elem in elements:
                        text = elem.inner_text().strip()
                        if text:
                            print(f"      {selector}: {text}")
                            break
            except:
                continue

        # 10. Page HTML Sample for Manual Review
        print(f"\n   J. HTML STRUCTURE SAMPLE:")
        try:
            # Get key sections of HTML
            head_title = page.query_selector("title")
            main_content = page.query_selector("main, #main, .main-content, .product-details")

            if head_title:
                print(f"      Page title: {head_title.inner_text()}")

            if main_content:
                print(f"      Main content structure: {main_content.evaluate('el => el.tagName + (el.className ? \".\" + el.className : \"\")')}")

        except:
            print(f"      HTML structure: Manual review needed")

        print(f"\n3. PARSING APPROACH RECOMMENDATIONS:")
        print(f"   Based on this analysis, the scraper should:")
        print(f"   - Use multiple selector fallbacks for each data field")
        print(f"   - Handle both ACDelco and GM Genuine Parts branding")
        print(f"   - Special attention to fitment data extraction")
        print(f"   - Cross-reference validation against part number")

    except Exception as e:
        print(f"   Error analyzing page structure: {e}")

def search_for_part(page, part_number):
    """Fallback: Search for the part if direct URL doesn't work"""
    print(f"   Searching for part {part_number} via search functionality...")

    try:
        # Go to main GMParts site
        page.goto("https://www.gmparts.com/", timeout=20000)
        time.sleep(3)

        # Look for search functionality
        search_selectors = [
            "input[type='search']", "input[name='search']",
            "input[name='q']", "#search", ".search-input"
        ]

        for selector in search_selectors:
            try:
                search_input = page.query_selector(selector)
                if search_input:
                    print(f"   Found search input: {selector}")
                    search_input.fill(part_number)
                    search_input.press("Enter")
                    time.sleep(5)

                    # Check if we found results
                    if part_number.lower() in page.inner_text("body").lower():
                        print(f"   [SUCCESS] Found {part_number} in search results!")
                        analyze_page_structure(page, part_number)
                    else:
                        print(f"   [INFO] Search performed but part not visible in results")
                    break
            except:
                continue

    except Exception as e:
        print(f"   Search fallback failed: {e}")

if __name__ == "__main__":
    analyze_acdelco_product_page()