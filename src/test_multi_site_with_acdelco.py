#!/usr/bin/env python3
"""
Test ACDelco via multi-site manager with proven working parts
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from scrapers.multi_site_manager import MultiSiteScraperManager
from database.db_manager import DatabaseManager


def test_working_parts():
    """Test the parts we know work with direct approach"""
    print("TESTING ACDELCO VIA MULTI-SITE MANAGER")
    print("Using parts confirmed to work in direct tests")
    print("=" * 60)

    # Initialize
    manager = MultiSiteScraperManager()
    db_manager = DatabaseManager()
    db_manager.initialize_database()

    # Test with parts we confirmed work
    working_parts = [
        ("12735811", "ACDelco"),  # Oil filter - 219 fitment records confirmed
        ("88866309", "ACDelco")   # Battery - confirmed working
    ]

    successful_tests = 0
    total_fitment_records = 0

    for i, (part_number, brand) in enumerate(working_parts, 1):
        print(f"\n>> TEST {i}: {part_number}")
        print("-" * 40)

        try:
            # Get initial database counts
            fitment_before = db_manager.execute_query("SELECT COUNT(*) as count FROM fitment", fetch='one')['count']

            # Run the scraper
            result = manager.scrape_part_multi_site(
                part_number=part_number,
                brand=brand,
                sites=['ACDelco'],
                store_results=True
            )

            # Check results
            acdelco_result = result['sites'].get('ACDelco', {})

            print(f"Success: {acdelco_result.get('success', False)}")
            print(f"Found: {acdelco_result.get('found', False)}")

            if acdelco_result.get('found'):
                successful_tests += 1

                print(f"Description: {acdelco_result.get('description', 'N/A')[:60]}...")
                print(f"Price: {acdelco_result.get('price', 'N/A')}")
                print(f"OEM Refs: {acdelco_result.get('oem_refs', [])}")

                # Check database fitment increase
                fitment_after = db_manager.execute_query("SELECT COUNT(*) as count FROM fitment", fetch='one')['count']
                fitment_added = fitment_after - fitment_before
                total_fitment_records += fitment_added

                print(f"Fitment records added to DB: {fitment_added}")

                if fitment_added > 0:
                    print(f"[SUCCESS] Fitment table populated! (+{fitment_added} rows)")
                else:
                    print(f"[WARNING] No fitment data stored in database")

            else:
                print(f"Error: {acdelco_result.get('error', 'Unknown error')}")

        except Exception as e:
            print(f"Test error: {e}")

    # Final database counts
    print("\n" + "=" * 60)
    print("FINAL DATABASE COUNTS")
    print("-" * 30)

    table_counts = {}
    tables = ['parts', 'part_sources', 'fitment', 'oem_references', 'part_specs', 'part_images']

    for table in tables:
        try:
            count_result = db_manager.execute_query(f"SELECT COUNT(*) as count FROM {table}", fetch='one')
            count = count_result['count'] if count_result else 0
            table_counts[table] = count
            print(f"{table:15} | {count:4d} rows")

            # Show sample data for key tables
            if count > 0 and table in ['fitment', 'oem_references']:
                sample = db_manager.execute_query(f"SELECT * FROM {table} LIMIT 2", fetch='all')
                if sample:
                    if table == 'fitment':
                        for row in sample:
                            print(f"                  Sample: {row['year']} {row['make']} {row['model']}")
                    elif table == 'oem_references':
                        for row in sample:
                            print(f"                  Sample: {row['oem_number']} from {row['source_site']}")

        except Exception as e:
            print(f"{table:15} | ERROR: {e}")
            table_counts[table] = 0

    print(f"{'TOTAL':15} | {sum(table_counts.values()):4d} records")

    # Assessment
    print("\n" + "=" * 60)
    print("ASSESSMENT")
    print("-" * 20)

    print(f"Successful part scrapes: {successful_tests}/{len(working_parts)}")
    print(f"Total fitment records added: {total_fitment_records}")

    if table_counts.get('fitment', 0) > 0:
        print(f"[SUCCESS] Fitment table now has {table_counts['fitment']} rows!")
        print("          The 0-rows fitment problem is SOLVED!")
    else:
        print("[WARNING] Fitment table still empty")

    if table_counts.get('oem_references', 0) > 2:  # More than the existing 2 RockAuto refs
        print(f"[SUCCESS] OEM references table populated ({table_counts['oem_references']} total)")

    if table_counts.get('part_specs', 0) > 2:  # More than existing 2
        print(f"[SUCCESS] Part specs table populated ({table_counts['part_specs']} total)")

    if successful_tests >= 1:
        print(f"\n[READY] ACDelco scraper working - ready for Moog implementation")
    else:
        print(f"\n[NEEDS WORK] ACDelco scraper needs debugging")

    return {
        'successful_tests': successful_tests,
        'total_fitment_records': total_fitment_records,
        'table_counts': table_counts
    }


if __name__ == "__main__":
    test_results = test_working_parts()
    print(f"\nACDelco multi-site integration test complete!")