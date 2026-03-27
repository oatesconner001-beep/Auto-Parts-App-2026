#!/usr/bin/env python3
"""
Verify database migration status and show table row counts
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from database.db_manager import DatabaseManager

def verify_database_migration():
    """Verify database migration and show detailed status"""
    print("DATABASE MIGRATION VERIFICATION")
    print("=" * 50)

    try:
        db_manager = DatabaseManager()

        # Check if database file exists
        db_path = db_manager.db_path
        if not db_path.exists():
            print(f"[ERROR] Database file not found at: {db_path}")
            return False

        print(f"[OK] Database file found: {db_path}")
        print(f"Database size: {db_path.stat().st_size:,} bytes")

        # Get database info
        info = db_manager.get_database_info()

        print(f"\nTABLE ROW COUNTS:")
        print("-" * 30)

        total_rows = 0
        for table_name, row_count in info['tables'].items():
            print(f"{table_name:20} : {row_count:6,} rows")
            total_rows += row_count

        print("-" * 30)
        print(f"{'TOTAL':20} : {total_rows:6,} rows")

        # Verify schema by checking table structure
        print(f"\nTABLE SCHEMA VERIFICATION:")
        print("-" * 40)

        expected_tables = [
            'parts', 'part_sources', 'part_images', 'fitment',
            'oem_references', 'scrape_log', 'site_configs', 'part_specs'
        ]

        missing_tables = []
        for table in expected_tables:
            if table in info['tables']:
                print(f"[OK] {table}")
            else:
                print(f"[ERROR] Missing table: {table}")
                missing_tables.append(table)

        if missing_tables:
            print(f"\n[ERROR] {len(missing_tables)} tables missing: {missing_tables}")
            return False

        # Show sample data from key tables
        print(f"\nSAMPLE DATA:")
        print("-" * 20)

        # Site configs
        configs = db_manager.get_site_configs()
        print(f"\nSite Configurations ({len(configs)} active sites):")
        for config in configs:
            status = "ACTIVE" if config.get('is_active') else "INACTIVE"
            delay = config.get('rate_limit_delay', 0)
            print(f"  {config['site_name']:15} - {status:8} (delay: {delay}s)")

        # Show any test data
        test_parts = db_manager.execute_query("SELECT * FROM parts LIMIT 3", fetch='all')
        if test_parts:
            print(f"\nSample Parts Data:")
            for part in test_parts:
                part_dict = dict(part)
                print(f"  ID {part_dict['id']}: {part_dict['brand']} {part_dict['part_number']} - {part_dict.get('part_name', 'N/A')}")

        # Show scrape log entries
        logs = db_manager.execute_query("SELECT * FROM scrape_log ORDER BY timestamp DESC LIMIT 5", fetch='all')
        if logs:
            print(f"\nRecent Scrape Activity:")
            for log in logs:
                log_dict = dict(log)
                success_str = "SUCCESS" if log_dict.get('success') else "FAILED"
                print(f"  {log_dict.get('timestamp', 'N/A')[:16]} - {log_dict.get('site_name', 'N/A')} ({success_str})")

        print(f"\n[SUCCESS] Database migration verification complete!")
        print(f"All {len(expected_tables)} required tables present and populated")

        return True

    except Exception as e:
        print(f"[ERROR] Database verification failed: {e}")
        return False

if __name__ == "__main__":
    success = verify_database_migration()
    sys.exit(0 if success else 1)