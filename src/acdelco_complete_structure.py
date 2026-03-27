#!/usr/bin/env python3
"""
Complete structure analysis of the confirmed ACDelco product page
Extract exact selectors for all target data fields
"""

from playwright.sync_api import sync_playwright
import time

def complete_acdelco_structure_analysis():
    """Complete analysis of confirmed working product page"""

    product_url = "https://parts.gmparts.com/product/acdelco-gm-original-equipment-engine-oil-filter-12735811"
    print("COMPLETE ACDELCO PRODUCT PAGE STRUCTURE")
    print("=" * 50)
    print(f"Analyzing: {product_url}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        try:
            print(f"\n1. LOADING CONFIRMED PRODUCT PAGE...")
            response = page.goto(product_url, timeout=30000)
            time.sleep(5)

            if response.status == 200:
                print(f"   [SUCCESS] Product page loaded")
                print(f"   Title: {page.title()}")

                print(f"\n2. EXTRACTING ALL TARGET DATA FIELDS:")

                # Extract each target field with exact selectors
                extract_part_number(page)
                extract_product_name(page)
                extract_brand_info(page)
                extract_pricing(page)
                extract_description(page)
                extract_specifications(page)
                extract_images(page)
                extract_fitment_system(page)  # CRITICAL
                extract_oem_references(page)
                extract_availability(page)

                print(f"\n3. FITMENT DATA EXTRACTION APPROACH:")
                analyze_fitment_interaction(page)

                print(f"\n4. SCRAPING RECOMMENDATIONS:")
                provide_scraping_approach()

        except Exception as e:
            print(f"Error: {e}")

        browser.close()

def extract_part_number(page):
    """Extract GM part number with exact selector"""
    print(f"\n   A. PART NUMBER EXTRACTION:")

    selectors = [
        "*:contains('GM Part #')",
        "*:contains('12735811')",
        ".part-number", "#part-number",
        "[data-part-number]"
    ]

    for selector in selectors:
        try:
            if "*:contains" in selector:
                # Manual text search
                elements = page.query_selector_all("*")
                for elem in elements:
                    text = elem.inner_text()
                    if "GM Part #" in text and "12735811" in text:
                        print(f"      [FOUND] Text content: '{text.strip()}'")
                        tag = elem.evaluate("el => el.tagName")
                        classes = elem.get_attribute("class")
                        print(f"      Element: {tag}.{classes}")
                        break
            else:
                element = page.query_selector(selector)
                if element:
                    text = element.inner_text().strip()
                    print(f"      [FOUND] {selector}: {text}")
        except:
            continue

def extract_product_name(page):
    """Extract product name and description"""
    print(f"\n   B. PRODUCT NAME:")

    selectors = ["h1", ".product-title", ".part-title", ".product-name"]

    for selector in selectors:
        try:
            element = page.query_selector(selector)
            if element:
                text = element.inner_text().strip()
                if len(text) > 10:  # Valid product name
                    print(f"      [FOUND] {selector}: {text}")
                    break
        except:
            continue

def extract_brand_info(page):
    """Extract brand information"""
    print(f"\n   C. BRAND INFORMATION:")

    # Check page content for brand indicators
    page_text = page.inner_text("body")

    brands_to_check = [
        ("ACDelco", "ACDelco" in page_text),
        ("GM Original Equipment", "GM Original Equipment" in page_text),
        ("GM Genuine Parts", "GM Genuine Parts" in page_text),
        ("General Motors", "General Motors" in page_text)
    ]

    for brand, found in brands_to_check:
        if found:
            print(f"      [FOUND] Brand indicator: {brand}")

def extract_pricing(page):
    """Extract pricing information"""
    print(f"\n   D. PRICING:")

    price_selectors = [
        "*:contains('MSRP')", "*:contains('$')",
        ".price", ".cost", ".msrp",
        "[data-price]", ".product-price"
    ]

    for selector in price_selectors:
        try:
            if "*:contains" in selector:
                search_term = selector.split("'")[1]
                elements = page.query_selector_all("*")
                for elem in elements:
                    text = elem.inner_text()
                    if search_term in text and "$" in text:
                        print(f"      [FOUND] Price text: '{text.strip()}'")
                        break
            else:
                elements = page.query_selector_all(selector)
                for elem in elements:
                    text = elem.inner_text().strip()
                    if "$" in text:
                        print(f"      [FOUND] {selector}: {text}")
                        break
        except:
            continue

def extract_description(page):
    """Extract product description"""
    print(f"\n   E. DESCRIPTION:")

    desc_selectors = [
        ".description", ".product-description",
        "*:contains('Helps keep abrasive')",
        ".details", ".product-details"
    ]

    for selector in desc_selectors:
        try:
            if "*:contains" in selector:
                page_text = page.inner_text("body")
                if "Helps keep abrasive" in page_text:
                    print(f"      [FOUND] Description contains: 'Helps keep abrasive particles...'")
            else:
                element = page.query_selector(selector)
                if element:
                    text = element.inner_text().strip()
                    if len(text) > 20:
                        print(f"      [FOUND] {selector}: {text[:100]}...")
        except:
            continue

def extract_specifications(page):
    """Extract technical specifications"""
    print(f"\n   F. SPECIFICATIONS:")

    spec_selectors = [
        ".specifications", ".specs", ".technical-data",
        ".product-specs", ".attributes", ".features"
    ]

    for selector in spec_selectors:
        try:
            elements = page.query_selector_all(selector)
            for elem in elements:
                text = elem.inner_text().strip()
                if len(text) > 10:
                    print(f"      [FOUND] {selector}: {text[:100]}...")
                    break
        except:
            continue

def extract_images(page):
    """Extract product images"""
    print(f"\n   G. PRODUCT IMAGES:")

    image_selectors = [
        "img[src*='product']", "img[src*='part']",
        ".product-image img", ".part-image img",
        "img[alt*='12735811']", "img[alt*='Oil Filter']"
    ]

    found_images = []
    for selector in image_selectors:
        try:
            images = page.query_selector_all(selector)
            for img in images:
                src = img.get_attribute("src")
                alt = img.get_attribute("alt")
                if src and src not in found_images:
                    print(f"      [FOUND] Image: {src}")
                    if alt:
                        print(f"        Alt text: {alt}")
                    found_images.append(src)
        except:
            continue

def extract_fitment_system(page):
    """CRITICAL: Analyze the fitment system"""
    print(f"\n   H. FITMENT SYSTEM (CRITICAL FOR TABLE POPULATION):")

    # Look for vehicle fit elements
    fitment_selectors = [
        "*:contains('Check Vehicle Fit')",
        "*:contains('Tell us more about your vehicle')",
        ".vehicle-fit", ".fitment", ".compatibility",
        "button[data-vehicle]", "[data-fit]"
    ]

    for selector in fitment_selectors:
        try:
            if "*:contains" in selector:
                search_term = selector.split("'")[1]
                if search_term in page.inner_text("body"):
                    print(f"      [FOUND] Fitment text: '{search_term}'")

                    # Look for associated interactive elements
                    buttons = page.query_selector_all("button")
                    for btn in buttons:
                        btn_text = btn.inner_text().strip()
                        if "vehicle" in btn_text.lower() or "fit" in btn_text.lower():
                            print(f"        Interactive element: '{btn_text}'")
                            onclick = btn.get_attribute("onclick")
                            data_attrs = btn.evaluate("el => Array.from(el.attributes).map(attr => `${attr.name}=${attr.value}`).join(', ')")
                            print(f"        Button attributes: {data_attrs}")
                            break
            else:
                elements = page.query_selector_all(selector)
                if elements:
                    print(f"      [FOUND] Fitment element: {selector}")
        except:
            continue

def extract_oem_references(page):
    """Extract OEM cross-references"""
    print(f"\n   I. OEM CROSS-REFERENCES:")

    # We know from preview that ACDelco Part # PF63 is shown
    oem_selectors = [
        "*:contains('ACDelco Part #')",
        "*:contains('PF63')",
        ".cross-reference", ".oem-reference",
        ".alternate-part"
    ]

    for selector in oem_selectors:
        try:
            if "*:contains" in selector:
                search_term = selector.split("'")[1]
                elements = page.query_selector_all("*")
                for elem in elements:
                    text = elem.inner_text()
                    if search_term in text:
                        print(f"      [FOUND] OEM reference: '{text.strip()}'")
                        break
            else:
                element = page.query_selector(selector)
                if element:
                    text = element.inner_text().strip()
                    print(f"      [FOUND] {selector}: {text}")
        except:
            continue

def extract_availability(page):
    """Extract availability/stock information"""
    print(f"\n   J. AVAILABILITY:")

    avail_selectors = [
        "*:contains('CURRENT SELLER')",
        "*:contains('Select Seller')",
        ".availability", ".stock", ".in-stock"
    ]

    for selector in avail_selectors:
        try:
            if "*:contains" in selector:
                search_term = selector.split("'")[1]
                if search_term in page.inner_text("body"):
                    print(f"      [FOUND] Availability text: '{search_term}'")
            else:
                element = page.query_selector(selector)
                if element:
                    text = element.inner_text().strip()
                    print(f"      [FOUND] {selector}: {text}")
        except:
            continue

def analyze_fitment_interaction(page):
    """Analyze how to interact with fitment system to get vehicle data"""

    print(f"   CRITICAL - Fitment data appears to be behind 'Check Vehicle Fit'")
    print(f"   This likely requires:")
    print(f"   1. Click 'Check Vehicle Fit' or similar button")
    print(f"   2. Input vehicle year/make/model/engine")
    print(f"   3. Extract resulting fitment table")
    print(f"   4. Parse year/make/model/engine combinations")

    # Look for vehicle input forms
    form_elements = page.query_selector_all("input, select, button")
    vehicle_forms = []

    for elem in form_elements:
        try:
            placeholder = elem.get_attribute("placeholder") or ""
            name = elem.get_attribute("name") or ""
            id_attr = elem.get_attribute("id") or ""
            text = elem.inner_text().strip().lower()

            vehicle_keywords = ["year", "make", "model", "engine", "vehicle", "fit"]
            if any(keyword in (placeholder + name + id_attr + text).lower() for keyword in vehicle_keywords):
                tag = elem.evaluate("el => el.tagName")
                print(f"   Vehicle form element: {tag} - {name or id_attr or placeholder or text}")
                vehicle_forms.append(elem)
        except:
            continue

    if vehicle_forms:
        print(f"   [SUCCESS] Found {len(vehicle_forms)} vehicle-related form elements")
        print(f"   Scraper should interact with these to populate fitment table")
    else:
        print(f"   [INFO] No obvious vehicle forms - may need to trigger fitment display first")

def provide_scraping_approach():
    """Provide scraping approach recommendations"""

    print(f"   RECOMMENDED SCRAPING APPROACH:")
    print(f"   ")
    print(f"   1. URL PATTERN: https://parts.gmparts.com/product/[description]-[part-number]")
    print(f"   2. DATA EXTRACTION:")
    print(f"      - Part Number: Text search for 'GM Part #' + number")
    print(f"      - Product Name: H1 or title extraction")
    print(f"      - Brand: Text search 'ACDelco' vs 'GM Original Equipment'")
    print(f"      - Price: Text search 'MSRP' + dollar amount")
    print(f"      - OEM Refs: Text search 'ACDelco Part #' + cross-reference")
    print(f"      - Description: Product details text")
    print(f"      - Images: Standard image selectors")
    print(f"   ")
    print(f"   3. FITMENT DATA (CRITICAL):")
    print(f"      - Interact with 'Check Vehicle Fit' system")
    print(f"      - May require vehicle input simulation")
    print(f"      - Extract resulting fitment combinations")
    print(f"      - Populate fitment table with year/make/model/engine")
    print(f"   ")
    print(f"   4. INTEGRATION WITH MULTI-SITE SYSTEM:")
    print(f"      - Use standardized scraper interface")
    print(f"      - Store in SQLite parts, part_sources, fitment, oem_references tables")
    print(f"      - Rate limit: 2-3 seconds between requests")

if __name__ == "__main__":
    complete_acdelco_structure_analysis()