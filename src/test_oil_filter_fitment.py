#!/usr/bin/env python3
"""
Test the original oil filter part that showed extensive fitment data in pre-code review
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from scrapers.acdelco_scraper import ACDelcoScraper


def test_oil_filter_fitment():
    """Test the oil filter that had extensive fitment data"""
    print("TESTING OIL FILTER WITH FITMENT DATA")
    print("=" * 50)

    scraper = ACDelcoScraper(headless=False)

    # This is the part from our pre-code review that had extensive fitment data:
    # "Fits - 2011-2024 Buick Enclave ; 2011-2016 Buick LaCrosse ; 2016-2019 Cadillac ATS..."
    test_part = "12735811"
    test_brand = "ACDelco"

    print(f"Testing oil filter: {test_part}")
    print("This part showed extensive fitment data in pre-code review")
    print("-" * 50)

    result = scraper.scrape_part(test_part, test_brand)

    print(f"Success: {result['success']}")
    print(f"Found: {result['found']}")

    if result.get('success') and result.get('found'):
        print(f"Description: {result.get('description', 'N/A')}")
        print(f"Price: {result.get('price', 'N/A')}")
        print(f"OEM Refs: {result.get('oem_refs', [])}")
        print(f"Fitment Records: {len(result.get('fitment_data', []))}")

        if result.get('fitment_data'):
            print(f"\n[SUCCESS] Found {len(result['fitment_data'])} fitment records!")
            print("Sample fitment data:")
            for i, fit in enumerate(result['fitment_data'][:10]):
                print(f"  {fit.get('year')} {fit.get('make')} {fit.get('model')}")

            print("...")
            print(f"Total: {len(result['fitment_data'])} fitment combinations")

            # This should solve the fitment table 0-rows problem
            print(f"\n[CRITICAL] This will populate {len(result['fitment_data'])} rows in the fitment table!")

        else:
            print("\n[WARNING] No fitment data found - may need to debug extraction")

        # Show specs
        if result.get('specs'):
            print(f"\nSpecifications ({len(result['specs'])} specs):")
            for spec, value in result['specs'].items():
                print(f"  {spec}: {value}")

    else:
        print(f"Error: {result.get('error', 'Unknown error')}")
        print("This part may need manual verification or different search approach")

    return result


if __name__ == "__main__":
    test_result = test_oil_filter_fitment()

    if test_result['success'] and len(test_result.get('fitment_data', [])) > 0:
        print("\n" + "=" * 50)
        print("[SUCCESS] Oil filter fitment extraction working!")
        print("Ready to test all 5 parts with full database integration")
    else:
        print("\n[NEEDS INVESTIGATION] Fitment extraction needs debugging")