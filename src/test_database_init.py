#!/usr/bin/env python3
"""
Test script for multi-site database initialization
Verifies database creation, schema, and basic operations
"""

import sys
import os
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent))

from database.db_manager import DatabaseManager, initialize_multi_site_database


def test_database_initialization():
    """Test complete database initialization process"""
    print(">> Testing Multi-Site Database Initialization")
    print("=" * 60)

    # Initialize database
    db_manager = initialize_multi_site_database()

    if not db_manager:
        print("[ERROR] Database initialization failed")
        return False

    print("\n--> Testing Database Operations...")

    # Test 1: Add a test part
    print("\n1. Testing part creation...")
    part_id = db_manager.add_part(
        part_number="TEST123",
        brand="TEST_BRAND",
        part_name="Test Engine Mount",
        category="ENGINE MOUNT",
        subcategory="Motor Mount"
    )

    if part_id:
        print(f"   [OK] Created test part with ID: {part_id}")
    else:
        print("   [ERROR] Failed to create test part")
        return False

    # Test 2: Add part source data
    print("\n2. Testing part source creation...")
    source_success = db_manager.add_part_source(
        part_id=part_id,
        site_name="RockAuto",
        site_part_number="RA_TEST123",
        availability_status="In Stock",
        price=25.99,
        product_url="https://www.rockauto.com/test123",
        scrape_success=True
    )

    if source_success:
        print("   [OK] Created test part source data")
    else:
        print("   [ERROR] Failed to create part source data")
        return False

    # Test 3: Log scraping activity
    print("\n3. Testing scrape logging...")
    log_success = db_manager.add_scrape_log(
        site_name="RockAuto",
        scrape_type="search",
        search_term="TEST123",
        success=True,
        rows_collected=1,
        duration_seconds=2.5,
        user_agent="Parts Agent Test"
    )

    if log_success:
        print("   [OK] Created test scrape log entry")
    else:
        print("   [ERROR] Failed to create scrape log entry")
        return False

    # Test 4: Query operations
    print("\n4. Testing query operations...")

    # Get site configs
    configs = db_manager.get_site_configs()
    print(f"   [OK] Found {len(configs)} active site configurations:")
    for config in configs:
        print(f"      - {config['site_name']}: {config['base_url']} (delay: {config['rate_limit_delay']}s)")

    # Get part by number
    test_part = db_manager.get_part_by_number("TEST123", "TEST_BRAND")
    if test_part:
        print(f"   [OK] Retrieved test part: {test_part['part_name']}")
    else:
        print("   [ERROR] Failed to retrieve test part")
        return False

    # Get parts with sources
    parts_with_sources = db_manager.get_parts_with_sources(limit=5)
    print(f"   [OK] Found {len(parts_with_sources)} parts with source data")

    # Get site performance
    performance = db_manager.get_site_performance()
    print(f"   [OK] Retrieved performance data for {len(performance)} sites")

    # Test 5: Database info
    print("\n5. Testing database information...")
    info = db_manager.get_database_info()
    print(f"   STATS: Database Information:")
    print(f"      Path: {info['database_path']}")
    print(f"      Size: {info['database_size']:,} bytes")
    print(f"      Total Records: {info['total_records']}")
    print(f"      Tables:")
    for table, count in info['tables'].items():
        print(f"         - {table}: {count} records")

    print("\nSUCCESS: All database tests completed successfully!")
    print("\nNOTE: Database is ready for multi-site scraping operations")
    return True


def cleanup_test_data(db_manager: DatabaseManager):
    """Clean up test data"""
    print("\nCLEANUP: Cleaning up test data...")

    # Remove test part and related data (CASCADE will handle related records)
    db_manager.execute_query("DELETE FROM parts WHERE part_number = 'TEST123'")
    db_manager.execute_query("DELETE FROM scrape_log WHERE site_name = 'RockAuto' AND search_term = 'TEST123'")

    print("   [OK] Test data cleaned up")


if __name__ == "__main__":
    success = test_database_initialization()

    if success:
        print("\n" + "="*60)
        print("READY: MULTI-SITE DATABASE READY FOR PRODUCTION")
        print("="*60)
        print("\nNext Steps:")
        print("1. Create site-specific scrapers for each target site")
        print("2. Build multi-site management interface")
        print("3. Implement cross-site part matching")
        print("4. Add GUI integration for database operations")

        # Optionally clean up test data
        response = input("\nClean up test data? (y/n): ").strip().lower()
        if response == 'y':
            db_manager = DatabaseManager()
            cleanup_test_data(db_manager)
    else:
        print("\n[ERROR] Database initialization test failed")
        sys.exit(1)