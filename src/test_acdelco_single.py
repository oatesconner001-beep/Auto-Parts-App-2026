#!/usr/bin/env python3
"""
Test single ACDelco part to verify the improved scraper works
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from scrapers.acdelco_scraper import ACDelcoScraper


def test_single_part():
    """Test one part with the improved scraper"""
    print("TESTING IMPROVED ACDELCO SCRAPER")
    print("=" * 40)

    scraper = ACDelcoScraper(headless=False)  # Visible for debugging

    # Test with a part we know is in the catalog
    test_part = "88866309"  # Found in catalog during debug
    test_brand = "ACDelco"

    print(f"Testing part: {test_part}")
    print("-" * 30)

    result = scraper.scrape_part(test_part, test_brand)

    print(f"Success: {result['success']}")
    print(f"Found: {result['found']}")
    print(f"Product URL: {result.get('product_url', 'N/A')}")
    print(f"Description: {result.get('description', 'N/A')}")
    print(f"Price: {result.get('price', 'N/A')}")
    print(f"Brand: {result.get('brand', 'N/A')}")
    print(f"OEM Refs: {result.get('oem_refs', [])}")
    print(f"Fitment Records: {len(result.get('fitment_data', []))}")
    print(f"Specifications: {len(result.get('specs', {}))}")

    if result.get('fitment_data'):
        print("\nSample Fitment Data:")
        for i, fit in enumerate(result['fitment_data'][:5]):
            print(f"  {fit.get('year')} {fit.get('make')} {fit.get('model')}")

    if result.get('error'):
        print(f"Error: {result['error']}")

    return result


if __name__ == "__main__":
    test_result = test_single_part()

    print("\n" + "=" * 40)
    if test_result['success'] and test_result['found']:
        print("[SUCCESS] Improved scraper is working!")
    else:
        print("[FAILED] Scraper still needs fixes")