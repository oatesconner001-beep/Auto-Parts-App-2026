#!/usr/bin/env python3
"""
Analysis of ACDelco product pages from the actual catalog where we found the parts
Navigate to brake catalog and analyze real product pages
"""

from playwright.sync_api import sync_playwright
import time
import re

def analyze_acdelco_from_catalog():
    """Analyze ACDelco by going to the catalog where we found the parts"""

    print("ACDELCO CATALOG-BASED ANALYSIS")
    print("Navigating to brake catalog where we found the 5 verified parts")
    print("=" * 55)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        try:
            # Go to the brake catalog where we originally found the parts
            catalog_url = "https://parts.gmparts.com/categories/brake-system/brake-pads-shoes/"
            print(f"1. LOADING CATALOG: {catalog_url}")

            response = page.goto(catalog_url, timeout=30000)
            print(f"   Status: {response.status}")
            time.sleep(5)

            if response.status == 200:
                page_title = page.title()
                print(f"   Title: {page_title}")
                print(f"   URL: {page.url}")

                # Look for our verified part numbers on this page
                page_text = page.inner_text("body")
                verified_parts = ['12735811', '84801575', '19474058', '88866309', '19367762']

                print(f"\n2. CHECKING FOR VERIFIED PARTS:")
                found_parts = []
                for part in verified_parts:
                    if part in page_text:
                        found_parts.append(part)
                        print(f"   [FOUND]: {part}")
                    else:
                        print(f"   [NOT VISIBLE]: {part}")

                if found_parts:
                    print(f"\n3. ANALYZING FIRST FOUND PART: {found_parts[0]}")
                    analyze_part_in_catalog(page, found_parts[0])
                else:
                    print(f"\n3. NO PARTS VISIBLE - ANALYZING CATALOG STRUCTURE:")
                    analyze_catalog_structure(page)

            else:
                print(f"   Failed to load catalog: {response.status}")

        except Exception as e:
            print(f"Error: {e}")

        browser.close()

def analyze_part_in_catalog(page, part_number):
    """Analyze how a specific part appears in the catalog"""

    try:
        print(f"   Analyzing part {part_number} in catalog context...")

        # Look for clickable elements containing this part number
        print(f"\n   A. PART LINKS AND CLICKABLE ELEMENTS:")

        # Try to find links or buttons related to this part
        selectors_to_check = [
            f"a[href*='{part_number}']",
            f"*[onclick*='{part_number}']",
            f"*[data-part*='{part_number}']",
            f"*[data-id*='{part_number}']"
        ]

        clickable_element = None
        for selector in selectors_to_check:
            elements = page.query_selector_all(selector)
            if elements:
                element = elements[0]
                print(f"      Found clickable element: {selector}")

                # Get the link or action
                href = element.get_attribute("href")
                onclick = element.get_attribute("onclick")
                data_attributes = element.evaluate("el => Array.from(el.attributes).map(attr => `${attr.name}=${attr.value}`).join(', ')")

                print(f"        Href: {href}")
                print(f"        Onclick: {onclick}")
                print(f"        Data attributes: {data_attributes}")

                clickable_element = element
                break

        if clickable_element:
            print(f"\n   B. CLICKING TO ACCESS PRODUCT PAGE:")
            try:
                # Click the element to go to product page
                clickable_element.click()
                time.sleep(5)

                new_url = page.url
                new_title = page.title()
                print(f"      New URL: {new_url}")
                print(f"      New Title: {new_title}")

                # Check if we're on a product page
                if part_number in page.inner_text("body") and new_url != page.url:
                    print(f"      [SUCCESS] Reached product page for {part_number}")
                    analyze_product_page_structure(page, part_number)
                else:
                    print(f"      [INFO] Click succeeded but may not be product page")
                    analyze_current_page_content(page, part_number)

            except Exception as e:
                print(f"      [ERROR] Click failed: {e}")
        else:
            print(f"\n   B. NO DIRECT CLICKABLE ELEMENT FOUND")
            print(f"      Analyzing part context in catalog listing...")
            analyze_part_context_in_listing(page, part_number)

    except Exception as e:
        print(f"   Error analyzing part in catalog: {e}")

def analyze_catalog_structure(page):
    """Analyze the catalog structure if parts aren't directly visible"""

    try:
        print(f"   Examining catalog page structure...")

        # Look for product listings, cards, or rows
        print(f"\n   A. PRODUCT LISTING STRUCTURE:")

        listing_selectors = [
            ".product", ".part", ".item", ".product-item",
            ".product-card", ".part-listing", ".result",
            "tr", ".row", ".grid-item"
        ]

        product_elements = []
        for selector in listing_selectors:
            elements = page.query_selector_all(selector)
            if elements and len(elements) > 1:  # Multiple elements suggest listings
                print(f"      Found {len(elements)} elements with selector: {selector}")

                # Analyze first few elements
                for i, elem in enumerate(elements[:3]):
                    try:
                        text = elem.inner_text().strip()
                        if len(text) > 10 and len(text) < 500:  # Reasonable product info
                            print(f"        Item {i+1}: {text[:100]}...")

                            # Check if this contains part numbers
                            part_numbers = re.findall(r'\b\d{8,11}\b', text)
                            if part_numbers:
                                print(f"          Found part numbers: {part_numbers}")
                                product_elements.append((elem, part_numbers[0]))
                    except:
                        continue

                if product_elements:
                    break

        if product_elements:
            print(f"\n   B. ANALYZING FIRST PRODUCT ELEMENT:")
            first_product, first_part = product_elements[0]
            analyze_product_element(first_product, first_part)
        else:
            print(f"\n   B. NO CLEAR PRODUCT LISTINGS FOUND")
            print(f"      Page might use dynamic loading or complex structure")

    except Exception as e:
        print(f"   Error analyzing catalog structure: {e}")

def analyze_part_context_in_listing(page, part_number):
    """Find and analyze the context around a part number in the listing"""

    try:
        # Look for the part number in the page content
        page_html = page.content()

        if part_number in page_html:
            print(f"      Found {part_number} in page HTML")

            # Try to find the containing element
            elements = page.query_selector_all("*")
            for element in elements:
                try:
                    element_text = element.inner_text()
                    if part_number in element_text and 10 < len(element_text) < 500:
                        print(f"      Part context: {element_text[:200]}...")

                        # Look for links within this element
                        links = element.query_selector_all("a")
                        for link in links:
                            href = link.get_attribute("href")
                            link_text = link.inner_text()
                            if href and (part_number in href or part_number in link_text):
                                print(f"        Product link: {href}")
                                print(f"        Link text: {link_text}")
                        break
                except:
                    continue

    except Exception as e:
        print(f"      Error analyzing part context: {e}")

def analyze_product_element(element, part_number):
    """Analyze a specific product element structure"""

    try:
        print(f"      Analyzing product element for part: {part_number}")

        # Get element details
        tag_name = element.evaluate("el => el.tagName")
        class_name = element.get_attribute("class")
        print(f"        Element: {tag_name}.{class_name}")

        # Look for sub-elements
        print(f"        Sub-elements:")

        sub_selectors = [
            "a", "img", ".price", ".name", ".description",
            ".part-number", ".brand", "button"
        ]

        for selector in sub_selectors:
            sub_elements = element.query_selector_all(selector)
            for sub_elem in sub_elements:
                try:
                    text = sub_elem.inner_text().strip()
                    href = sub_elem.get_attribute("href")
                    src = sub_elem.get_attribute("src")

                    info = f"{selector}: "
                    if text: info += f"'{text}' "
                    if href: info += f"href='{href}' "
                    if src: info += f"src='{src}' "

                    print(f"          {info}")
                except:
                    continue

    except Exception as e:
        print(f"      Error analyzing product element: {e}")

def analyze_product_page_structure(page, part_number):
    """Analyze actual product page structure - this is what we need for scraping"""

    print(f"\n   C. PRODUCT PAGE STRUCTURE ANALYSIS:")
    print(f"      [SUCCESS] On product page for part: {part_number}")

    try:
        # This is the critical analysis for scraper development
        page_url = page.url
        page_title = page.title()

        print(f"      Product URL: {page_url}")
        print(f"      Product Title: {page_title}")

        # Analyze all the target data fields
        target_fields = {
            "Part Number": [".part-number", ".partnum", "#part-number", f"*:contains('{part_number}')"],
            "Product Name": ["h1", ".product-name", ".title", ".part-name"],
            "Brand": [".brand", ".manufacturer", "*:contains('ACDelco')", "*:contains('GM')"],
            "Price": [".price", ".cost", ".msrp", "*[class*='price']"],
            "Description": [".description", ".product-description", ".details"],
            "Specifications": [".specs", ".specifications", ".technical-data", ".attributes"],
            "Images": ["img[src*='product']", "img[src*='part']", ".product-image img"],
            "Fitment": [".fitment", ".compatibility", ".vehicle-fit", ".applications", "table"],
            "OEM References": [".oem", ".cross-reference", ".replaces", "*:contains('OEM')"],
            "Availability": [".availability", ".stock", ".in-stock", "*:contains('Available')"]
        }

        for field_name, selectors in target_fields.items():
            print(f"\n      {field_name.upper()}:")
            found = False

            for selector in selectors:
                try:
                    if "*:contains" in selector:
                        # Text-based search
                        search_term = selector.split("'")[1] if "'" in selector else part_number
                        if search_term.lower() in page.inner_text("body").lower():
                            print(f"        [OK] Found via text search: '{search_term}'")
                            found = True
                    else:
                        # Element-based search
                        elements = page.query_selector_all(selector)
                        for elem in elements:
                            text = elem.inner_text().strip()
                            if text and len(text) > 2:
                                print(f"        [OK] {selector}: {text[:100]}")
                                found = True
                                break

                    if found:
                        break
                except:
                    continue

            if not found:
                print(f"        [NOT FOUND] Not found - needs manual identification")

        print(f"\n      SCRAPING APPROACH SUMMARY:")
        print(f"      - Product page accessible via catalog navigation")
        print(f"      - URL pattern: {page_url}")
        print(f"      - Data extraction feasible with identified selectors")
        print(f"      - Special attention needed for fields marked as 'Not found'")

    except Exception as e:
        print(f"      Error in product page analysis: {e}")

def analyze_current_page_content(page, part_number):
    """Analyze current page content if it's not a clear product page"""

    try:
        print(f"      Analyzing current page content for part: {part_number}")

        # Get page basics
        url = page.url
        title = page.title()
        body_preview = page.inner_text("body")[:500]

        print(f"      Current URL: {url}")
        print(f"      Current Title: {title}")
        print(f"      Content Preview: {body_preview}...")

        # Check what kind of page this is
        if "search" in url.lower() or "search" in title.lower():
            print(f"      [INFO] This appears to be a search results page")
        elif "catalog" in url.lower() or "category" in url.lower():
            print(f"      [INFO] This appears to be a catalog/category page")
        elif part_number in body_preview:
            print(f"      [INFO] Part number is visible, may be product listing")
        else:
            print(f"      [INFO] Unclear page type, needs investigation")

    except Exception as e:
        print(f"      Error analyzing current page: {e}")

if __name__ == "__main__":
    analyze_acdelco_from_catalog()