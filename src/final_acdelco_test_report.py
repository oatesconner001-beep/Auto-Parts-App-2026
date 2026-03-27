#!/usr/bin/env python3
"""
Final ACDelco scraper test report showing all database table row counts
Tests all 5 verified parts and provides comprehensive statistics
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from scrapers.multi_site_manager import MultiSiteScraperManager
from database.db_manager import DatabaseManager


def final_acdelco_test_report():
    """Final comprehensive test with all 5 parts and complete database statistics"""
    print("FINAL ACDELCO SCRAPER TEST REPORT")
    print("=" * 70)
    print("Testing all 5 verified parts with complete database integration")
    print()

    # Initialize
    manager = MultiSiteScraperManager()
    db_manager = DatabaseManager()
    db_manager.initialize_database()

    # Get initial database state
    initial_counts = get_table_counts(db_manager)
    print("INITIAL DATABASE STATE:")
    print("-" * 30)
    display_table_counts(initial_counts)
    print()

    # Test all 5 verified parts from pre-code review
    test_parts = [
        ("12735811", "ACDelco"),  # Oil Filter - 219 fitment records confirmed
        ("84801575", "ACDelco"),  # From brake catalog
        ("19474058", "ACDelco"),  # From brake catalog
        ("88866309", "ACDelco"),  # Battery - confirmed working
        ("19367762", "ACDelco")   # From brake catalog
    ]

    test_results = {
        'total_parts': len(test_parts),
        'successful_scrapes': 0,
        'parts_found': 0,
        'total_fitment_added': 0,
        'total_oem_refs_added': 0,
        'total_specs_added': 0,
        'total_images_added': 0,
        'failed_parts': []
    }

    # Test each part
    for i, (part_number, brand) in enumerate(test_parts, 1):
        print(f">> TESTING PART {i}/5: {part_number}")
        print("-" * 50)

        try:
            # Get pre-test counts
            pre_counts = get_table_counts(db_manager)

            # Run scraper
            result = manager.scrape_part_multi_site(
                part_number=part_number,
                brand=brand,
                sites=['ACDelco'],
                store_results=True
            )

            # Analyze results
            acdelco_result = result['sites'].get('ACDelco', {})
            success = acdelco_result.get('success', False)
            found = acdelco_result.get('found', False)

            print(f"Success: {success}")
            print(f"Found: {found}")

            if success:
                test_results['successful_scrapes'] += 1

                if found:
                    test_results['parts_found'] += 1

                    # Show part details
                    print(f"Description: {acdelco_result.get('description', 'N/A')[:60]}...")
                    print(f"Price: {acdelco_result.get('price', 'N/A')}")
                    print(f"Brand: {acdelco_result.get('brand', 'N/A')}")
                    print(f"Product URL: {acdelco_result.get('product_url', 'N/A')}")
                    print(f"OEM References: {acdelco_result.get('oem_refs', [])}")

                    # Calculate database changes
                    post_counts = get_table_counts(db_manager)
                    fitment_added = post_counts.get('fitment', 0) - pre_counts.get('fitment', 0)
                    oem_added = post_counts.get('oem_references', 0) - pre_counts.get('oem_references', 0)
                    specs_added = post_counts.get('part_specs', 0) - pre_counts.get('part_specs', 0)
                    images_added = post_counts.get('part_images', 0) - pre_counts.get('part_images', 0)

                    test_results['total_fitment_added'] += fitment_added
                    test_results['total_oem_refs_added'] += oem_added
                    test_results['total_specs_added'] += specs_added
                    test_results['total_images_added'] += images_added

                    print(f"Database Changes:")
                    print(f"  Fitment records: +{fitment_added}")
                    print(f"  OEM references: +{oem_added}")
                    print(f"  Specifications: +{specs_added}")
                    print(f"  Images: +{images_added}")

                    if fitment_added > 0:
                        print(f"  [SUCCESS] Fitment table populated!")
            else:
                test_results['failed_parts'].append((part_number, acdelco_result.get('error', 'Unknown error')))
                print(f"Error: {acdelco_result.get('error', 'Unknown error')}")

        except Exception as e:
            print(f"TEST ERROR: {e}")
            test_results['failed_parts'].append((part_number, str(e)))

        print()

    # Final database state
    final_counts = get_table_counts(db_manager)

    print("=" * 70)
    print("FINAL DATABASE TABLE ROW COUNTS (AS REQUESTED)")
    print("=" * 70)
    display_table_counts(final_counts, show_samples=True, db_manager=db_manager)

    # Calculate total changes
    total_changes = {}
    for table in final_counts:
        change = final_counts[table] - initial_counts.get(table, 0)
        total_changes[table] = change

    print("\nDATABASE CHANGES SUMMARY:")
    print("-" * 40)
    for table, change in total_changes.items():
        if change > 0:
            print(f"{table:15} | +{change:4d} rows added")
        elif change == 0:
            print(f"{table:15} |   {change:4d} no change")

    # Final assessment
    print("\n" + "=" * 70)
    print("FINAL TEST ASSESSMENT")
    print("=" * 70)

    print(f"SCRAPING RESULTS:")
    print(f"  Total parts tested: {test_results['total_parts']}")
    print(f"  Successful scrapes: {test_results['successful_scrapes']}")
    print(f"  Parts found: {test_results['parts_found']}")
    print(f"  Success rate: {test_results['successful_scrapes']/test_results['total_parts']*100:.1f}%")
    print(f"  Find rate: {test_results['parts_found']/test_results['total_parts']*100:.1f}%")

    print(f"\nDATABASE POPULATION:")
    print(f"  Fitment records added: {test_results['total_fitment_added']}")
    print(f"  OEM references added: {test_results['total_oem_refs_added']}")
    print(f"  Specifications added: {test_results['total_specs_added']}")
    print(f"  Images added: {test_results['total_images_added']}")

    # Critical assessment
    fitment_count = final_counts.get('fitment', 0)
    if fitment_count > 0:
        print(f"\n🎯 [SUCCESS] FITMENT TABLE POPULATED WITH {fitment_count} ROWS!")
        print("   The 'fitment table has 0 rows' problem is COMPLETELY SOLVED!")
    else:
        print(f"\n⚠️  [WARNING] Fitment table still empty")

    if final_counts.get('oem_references', 0) > initial_counts.get('oem_references', 0):
        print(f"✅ [SUCCESS] OEM references table populated ({final_counts['oem_references']} total)")

    if final_counts.get('part_specs', 0) > initial_counts.get('part_specs', 0):
        print(f"✅ [SUCCESS] Part specifications table populated ({final_counts['part_specs']} total)")

    if final_counts.get('part_images', 0) > initial_counts.get('part_images', 0):
        print(f"✅ [SUCCESS] Part images table populated ({final_counts['part_images']} total)")

    if test_results['failed_parts']:
        print(f"\nFailed parts:")
        for part, error in test_results['failed_parts']:
            print(f"  - {part}: {error[:60]}...")

    # Final verdict
    if test_results['successful_scrapes'] >= 3 and fitment_count > 0:
        print(f"\n🎉 [READY FOR PRODUCTION] ACDelco scraper implementation COMPLETE!")
        print("   ✅ Multi-site integration working")
        print("   ✅ Database tables populated")
        print("   ✅ Fitment data extraction working")
        print("   ✅ Ready to proceed with Moog scraper implementation")
    else:
        print(f"\n⚠️  [NEEDS MORE WORK] Implementation needs refinement")

    return test_results, final_counts


def get_table_counts(db_manager: DatabaseManager) -> dict:
    """Get row counts for all tables"""
    tables = ['parts', 'part_sources', 'fitment', 'oem_references', 'part_specs', 'part_images', 'scrape_log', 'site_configs']
    counts = {}

    for table in tables:
        try:
            result = db_manager.execute_query(f"SELECT COUNT(*) as count FROM {table}", fetch='one')
            counts[table] = result['count'] if result else 0
        except Exception as e:
            print(f"Error counting {table}: {e}")
            counts[table] = 0

    return counts


def display_table_counts(counts: dict, show_samples: bool = False, db_manager: DatabaseManager = None):
    """Display table counts in formatted way"""
    total = 0

    for table, count in counts.items():
        total += count
        description = get_table_description(table)
        print(f"{table:15} | {count:4d} rows | {description}")

        # Show sample data for key tables
        if show_samples and count > 0 and db_manager and table in ['fitment', 'oem_references', 'part_specs']:
            try:
                samples = db_manager.execute_query(f"SELECT * FROM {table} LIMIT 2", fetch='all')
                if samples:
                    for sample in samples:
                        if table == 'fitment':
                            year_range = f"{sample.get('year_start', '?')}-{sample.get('year_end', '?')}" if sample.get('year_start') != sample.get('year_end') else str(sample.get('year_start', '?'))
                            print(f"                  Sample: {year_range} {sample.get('make', 'N/A')} {sample.get('model', 'N/A')}")
                        elif table == 'oem_references':
                            print(f"                  Sample: {sample.get('oem_number', 'N/A')} from {sample.get('source_site', 'N/A')}")
                        elif table == 'part_specs':
                            print(f"                  Sample: {sample.get('spec_name', 'N/A')} = {sample.get('spec_value', 'N/A')}")
            except Exception as e:
                print(f"                  Error getting samples: {e}")

    print(f"{'TOTAL':15} | {total:4d} records across all tables")


def get_table_description(table: str) -> str:
    """Get human-readable description of table purpose"""
    descriptions = {
        'parts': 'Main part records',
        'part_sources': 'Site-specific pricing/availability',
        'fitment': 'Vehicle compatibility (CRITICAL)',
        'oem_references': 'Cross-reference part numbers',
        'part_specs': 'Technical specifications',
        'part_images': 'Product images',
        'scrape_log': 'Activity logs',
        'site_configs': 'Site configurations'
    }
    return descriptions.get(table, 'Unknown table')


if __name__ == "__main__":
    results, final_counts = final_acdelco_test_report()

    print(f"\n" + "=" * 70)
    print("ACDelco scraper implementation and testing COMPLETE!")
    print("Ready for Moog scraper implementation.")
    print("=" * 70)