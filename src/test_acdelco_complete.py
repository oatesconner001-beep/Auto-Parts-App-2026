#!/usr/bin/env python3
"""
Complete test of ACDelco scraper with all 5 verified parts
Show database table row counts as requested
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from scrapers.multi_site_manager import MultiSiteScraperManager
from database.db_manager import DatabaseManager


def test_all_acdelco_parts():
    """Test all 5 verified ACDelco parts and show database statistics"""
    print("COMPLETE ACDELCO SCRAPER TEST")
    print("=" * 60)
    print("Testing all 5 verified parts with database row counts")
    print()

    # Initialize managers
    manager = MultiSiteScraperManager()
    db_manager = DatabaseManager()
    db_manager.initialize_database()

    # 5 verified parts from pre-code review
    test_parts = [
        ("12735811", "ACDelco"),  # Oil Filter - confirmed working in analysis
        ("84801575", "ACDelco"),  # From brake catalog
        ("19474058", "ACDelco"),  # From brake catalog
        ("88866309", "ACDelco"),  # From brake catalog
        ("19367762", "ACDelco")   # From brake catalog
    ]

    results_summary = {
        'total_parts': len(test_parts),
        'successful_scrapes': 0,
        'failed_scrapes': 0,
        'parts_found': 0,
        'total_fitment_records': 0,
        'total_oem_references': 0,
        'total_specs': 0,
        'total_images': 0,
        'total_sources': 0
    }

    # Test each part
    for i, (part_number, brand) in enumerate(test_parts, 1):
        print(f">> TEST {i}/5: {part_number}")
        print("-" * 40)

        try:
            # Scrape the part via multi-site manager
            result = manager.scrape_part_multi_site(
                part_number=part_number,
                brand=brand,
                sites=['ACDelco'],
                store_results=True
            )

            # Analyze results
            acdelco_result = result['sites'].get('ACDelco', {})

            print(f"Success: {acdelco_result.get('success', False)}")
            print(f"Found: {acdelco_result.get('found', False)}")
            print(f"Product URL: {acdelco_result.get('product_url', 'N/A')}")
            print(f"Description: {acdelco_result.get('description', 'N/A')[:60]}...")
            print(f"Price: {acdelco_result.get('price', 'N/A')}")
            print(f"Brand: {acdelco_result.get('brand', 'N/A')}")
            print(f"OEM Refs: {acdelco_result.get('oem_refs', [])}")

            # Count fitment data
            fitment_count = len(acdelco_result.get('fitment_data', []))
            print(f"Fitment Records: {fitment_count}")

            # Count specs
            specs_count = len(acdelco_result.get('specs', {}))
            print(f"Specifications: {specs_count}")

            # Update summary
            if acdelco_result.get('success'):
                results_summary['successful_scrapes'] += 1
                if acdelco_result.get('found'):
                    results_summary['parts_found'] += 1
                    results_summary['total_fitment_records'] += fitment_count
                    results_summary['total_oem_references'] += len(acdelco_result.get('oem_refs', []))
                    results_summary['total_specs'] += specs_count
                    if acdelco_result.get('image_url'):
                        results_summary['total_images'] += 1
                    results_summary['total_sources'] += 1
            else:
                results_summary['failed_scrapes'] += 1

            if acdelco_result.get('error'):
                print(f"Error: {acdelco_result['error']}")

        except Exception as e:
            print(f"TEST ERROR: {e}")
            results_summary['failed_scrapes'] += 1

        print()

    # Show overall test summary
    print("=" * 60)
    print("OVERALL TEST SUMMARY")
    print("-" * 30)
    print(f"Total Parts Tested: {results_summary['total_parts']}")
    print(f"Successful Scrapes: {results_summary['successful_scrapes']}")
    print(f"Failed Scrapes: {results_summary['failed_scrapes']}")
    print(f"Parts Found: {results_summary['parts_found']}")
    print(f"Success Rate: {results_summary['successful_scrapes']/results_summary['total_parts']*100:.1f}%")
    print()

    # Show data collection summary
    print("DATA COLLECTION SUMMARY")
    print("-" * 30)
    print(f"Total Fitment Records: {results_summary['total_fitment_records']}")
    print(f"Total OEM References: {results_summary['total_oem_references']}")
    print(f"Total Specifications: {results_summary['total_specs']}")
    print(f"Total Images Found: {results_summary['total_images']}")
    print(f"Total Part Sources: {results_summary['total_sources']}")
    print()

    # CRITICAL: Show database table row counts as requested
    show_database_row_counts(db_manager)

    return results_summary


def show_database_row_counts(db_manager: DatabaseManager):
    """Show row counts from all database tables as requested by user"""
    print("=" * 60)
    print("DATABASE TABLE ROW COUNTS")
    print("-" * 30)

    # Tables to check with their purposes
    tables_to_check = [
        ('parts', 'Main part records'),
        ('part_sources', 'Site-specific data'),
        ('fitment', 'Vehicle compatibility (CRITICAL)'),
        ('oem_references', 'Cross-references'),
        ('part_specs', 'Technical specifications'),
        ('part_images', 'Product images'),
        ('scrape_log', 'Activity logs'),
        ('site_configs', 'Site configurations')
    ]

    total_records = 0

    for table_name, description in tables_to_check:
        try:
            # Get row count for this table
            result = db_manager.execute_query(
                f"SELECT COUNT(*) as count FROM {table_name}",
                fetch='one'
            )

            count = result['count'] if result else 0
            total_records += count

            print(f"{table_name:15} | {count:4d} rows | {description}")

            # Show sample data for key tables
            if count > 0 and table_name in ['fitment', 'oem_references', 'part_specs']:
                sample_query = f"SELECT * FROM {table_name} LIMIT 2"
                samples = db_manager.execute_query(sample_query, fetch='all')

                if samples:
                    if table_name == 'fitment':
                        for sample in samples:
                            print(f"                  Sample: {sample['year']} {sample['make']} {sample['model']}")
                    elif table_name == 'oem_references':
                        for sample in samples:
                            print(f"                  Sample: {sample['oem_number']} from {sample['source_site']}")
                    elif table_name == 'part_specs':
                        for sample in samples:
                            print(f"                  Sample: {sample['spec_name']} = {sample['spec_value']}")

        except Exception as e:
            print(f"{table_name:15} | ERROR | {e}")

    print(f"{'TOTAL':15} | {total_records:4d} records across all tables")
    print()

    # Check if fitment table population was successful (critical requirement)
    fitment_count_result = db_manager.execute_query(
        "SELECT COUNT(*) as count FROM fitment",
        fetch='one'
    )
    fitment_count = fitment_count_result['count'] if fitment_count_result else 0

    if fitment_count > 0:
        print(f"[SUCCESS] Fitment table populated with {fitment_count} records!")
        print("          This solves the 'fitment table has 0 rows' problem.")
    else:
        print("[WARNING] Fitment table is still empty - check scraper implementation")

    print()

    return total_records


if __name__ == "__main__":
    test_results = test_all_acdelco_parts()

    print("=" * 60)
    print("TEST COMPLETION")
    print("-" * 20)
    if test_results['successful_scrapes'] >= 3:
        print("[SUCCESS] ACDelco scraper ready for production")
        print("Ready to proceed with Moog scraper implementation")
    else:
        print("[WARNING] Some tests failed - review implementation")

    print("\nACDelco scraper implementation complete!")