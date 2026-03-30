#!/usr/bin/env python3
"""
Database Manager for Multi-Site Parts Agent
Handles SQLite database initialization, migrations, and operations
"""

import sqlite3
import os
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import json

class DatabaseManager:
    """Manages SQLite database for multi-site parts data storage"""

    def __init__(self, db_path: str = "data/parts_agent.db"):
        """Initialize database manager

        Args:
            db_path: Path to SQLite database file (relative to project root)
        """
        self.project_root = Path(__file__).parent.parent.parent
        self.db_path = self.project_root / db_path
        self.schema_path = self.project_root / "src" / "database" / "schema.sql"

        # Ensure data directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Setup logging
        self.logger = logging.getLogger(__name__)

    def initialize_database(self) -> bool:
        """Initialize database with schema if not exists

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Check if database exists and has tables
            needs_init = not self.db_path.exists()

            if not needs_init:
                # Check if tables exist
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    tables = cursor.fetchall()
                    needs_init = len(tables) == 0

            if needs_init:
                self.logger.info(f"Initializing database at {self.db_path}")
                return self._create_schema()
            else:
                self.logger.info("Database already initialized")
                return True

        except Exception as e:
            self.logger.error(f"Database initialization failed: {e}")
            return False

    def _create_schema(self) -> bool:
        """Create database schema from SQL file

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Read schema SQL
            if not self.schema_path.exists():
                raise FileNotFoundError(f"Schema file not found: {self.schema_path}")

            with open(self.schema_path, 'r', encoding='utf-8') as f:
                schema_sql = f.read()

            # Execute schema
            with sqlite3.connect(self.db_path) as conn:
                conn.executescript(schema_sql)
                conn.commit()

            self.logger.info("Database schema created successfully")
            return True

        except Exception as e:
            self.logger.error(f"Schema creation failed: {e}")
            return False

    def get_connection(self) -> sqlite3.Connection:
        """Get database connection with row factory

        Returns:
            sqlite3.Connection: Database connection
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        return conn

    def execute_query(self, query: str, params: tuple = (), fetch: str = None) -> Optional[Any]:
        """Execute SQL query with error handling

        Args:
            query: SQL query string
            params: Query parameters
            fetch: 'one', 'all', or None for no fetch

        Returns:
            Query results or None
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)

                if fetch == 'one':
                    return cursor.fetchone()
                elif fetch == 'all':
                    return cursor.fetchall()
                else:
                    conn.commit()
                    return cursor.rowcount

        except Exception as e:
            self.logger.error(f"Query execution failed: {query[:100]}... Error: {e}")
            return None

    def add_part(self, part_number: str, brand: str, part_name: str = None,
                 category: str = None, subcategory: str = None) -> Optional[int]:
        """Add new part to database

        Args:
            part_number: Manufacturer part number
            brand: Brand/manufacturer name
            part_name: Descriptive part name
            category: Part category
            subcategory: Part subcategory

        Returns:
            int: Part ID if successful, None otherwise
        """
        query = """
            INSERT OR IGNORE INTO parts (part_number, brand, part_name, category, subcategory)
            VALUES (?, ?, ?, ?, ?)
        """
        result = self.execute_query(query, (part_number, brand, part_name, category, subcategory))

        if result and result > 0:
            # Get the part ID
            get_id_query = "SELECT id FROM parts WHERE part_number = ? AND brand = ?"
            row = self.execute_query(get_id_query, (part_number, brand), fetch='one')
            return row['id'] if row else None
        return None

    def add_part_source(self, part_id: int, site_name: str, site_part_number: str = None,
                       availability_status: str = None, price: float = None,
                       sale_price: float = None, stock_quantity: int = None,
                       product_url: str = None, scrape_success: bool = True,
                       scrape_error: str = None, listing_id: str = None,
                       core_charge: float = None) -> bool:
        """Add site-specific part data

        Args:
            part_id: Foreign key to parts table
            site_name: Name of the site (e.g., 'RockAuto', 'PartsGeek')
            site_part_number: Site's internal part number
            availability_status: Availability status from site
            price: Current price
            sale_price: Sale price if on sale
            stock_quantity: Stock quantity
            product_url: Direct URL to product page
            scrape_success: Whether scraping was successful
            scrape_error: Error message if scraping failed
            listing_id: Unique identifier for multiple listings per part
            core_charge: Core charge fee for the part

        Returns:
            bool: True if successful, False otherwise
        """
        query = """
            INSERT OR IGNORE INTO part_sources
            (part_id, site_name, site_part_number, availability_status, price,
             sale_price, stock_quantity, product_url, scrape_success, scrape_error, listing_id, core_charge)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        result = self.execute_query(query, (
            part_id, site_name, site_part_number, availability_status,
            price, sale_price, stock_quantity, product_url, scrape_success, scrape_error, listing_id, core_charge
        ))
        return result is not None and result > 0

    def add_scrape_log(self, site_name: str, scrape_type: str, search_term: str = None,
                      success: bool = True, rows_collected: int = 0, rows_failed: int = 0,
                      duration_seconds: float = None, error_message: str = None,
                      user_agent: str = None, rate_limit_delay: float = None) -> bool:
        """Log scraping activity

        Args:
            site_name: Name of scraped site
            scrape_type: Type of scrape (search, detail, category)
            search_term: Search term used
            success: Whether scrape was successful
            rows_collected: Number of rows successfully collected
            rows_failed: Number of rows that failed
            duration_seconds: Time taken for scrape
            error_message: Error message if failed
            user_agent: User agent used
            rate_limit_delay: Delay used for rate limiting

        Returns:
            bool: True if successful, False otherwise
        """
        query = """
            INSERT INTO scrape_log
            (site_name, scrape_type, search_term, success, rows_collected,
             rows_failed, duration_seconds, error_message, user_agent, rate_limit_delay)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        result = self.execute_query(query, (
            site_name, scrape_type, search_term, success, rows_collected,
            rows_failed, duration_seconds, error_message, user_agent, rate_limit_delay
        ))
        return result is not None and result > 0

    def get_site_configs(self) -> List[Dict]:
        """Get all site configurations

        Returns:
            List of site config dictionaries
        """
        query = "SELECT * FROM site_configs WHERE is_active = 1"
        rows = self.execute_query(query, fetch='all')
        return [dict(row) for row in rows] if rows else []

    def update_site_config(self, site_name: str, **kwargs) -> bool:
        """Update site configuration

        Args:
            site_name: Name of site to update
            **kwargs: Fields to update

        Returns:
            bool: True if successful, False otherwise
        """
        if not kwargs:
            return False

        # Build dynamic update query
        fields = list(kwargs.keys())
        placeholders = ', '.join([f"{field} = ?" for field in fields])
        values = list(kwargs.values()) + [site_name]

        query = f"UPDATE site_configs SET {placeholders}, updated_at = CURRENT_TIMESTAMP WHERE site_name = ?"
        result = self.execute_query(query, tuple(values))
        return result is not None and result > 0

    def get_part_by_number(self, part_number: str, brand: str = None) -> Optional[Dict]:
        """Get part by part number and optionally brand

        Args:
            part_number: Part number to search for
            brand: Optional brand filter

        Returns:
            Dict: Part data or None if not found
        """
        if brand:
            query = "SELECT * FROM parts WHERE part_number = ? AND brand = ?"
            params = (part_number, brand)
        else:
            query = "SELECT * FROM parts WHERE part_number = ?"
            params = (part_number,)

        row = self.execute_query(query, params, fetch='one')
        return dict(row) if row else None

    def get_parts_with_sources(self, limit: int = 100) -> List[Dict]:
        """Get parts with their source data using the view

        Args:
            limit: Maximum number of results

        Returns:
            List of part dictionaries with source data
        """
        query = f"SELECT * FROM parts_with_sources LIMIT ?"
        rows = self.execute_query(query, (limit,), fetch='all')
        return [dict(row) for row in rows] if rows else []

    def get_site_performance(self) -> List[Dict]:
        """Get site performance metrics using the view

        Returns:
            List of site performance dictionaries
        """
        query = "SELECT * FROM site_performance"
        rows = self.execute_query(query, fetch='all')
        return [dict(row) for row in rows] if rows else []

    def backup_database(self, backup_path: str = None) -> bool:
        """Create database backup

        Args:
            backup_path: Optional custom backup path

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if backup_path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = f"data/backup/parts_agent_{timestamp}.db"

            backup_path = self.project_root / backup_path
            backup_path.parent.mkdir(parents=True, exist_ok=True)

            # Copy database
            import shutil
            shutil.copy2(self.db_path, backup_path)

            self.logger.info(f"Database backed up to {backup_path}")
            return True

        except Exception as e:
            self.logger.error(f"Database backup failed: {e}")
            return False

    def get_database_info(self) -> Dict[str, Any]:
        """Get database information and statistics

        Returns:
            Dict: Database information
        """
        info = {
            'database_path': str(self.db_path),
            'database_size': self.db_path.stat().st_size if self.db_path.exists() else 0,
            'tables': {},
            'total_records': 0
        }

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Get table info
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()

                for table in tables:
                    table_name = table[0]
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    count = cursor.fetchone()[0]
                    info['tables'][table_name] = count
                    info['total_records'] += count

        except Exception as e:
            self.logger.error(f"Failed to get database info: {e}")

        return info


def initialize_multi_site_database():
    """Initialize the multi-site database

    Returns:
        DatabaseManager: Initialized database manager
    """
    db_manager = DatabaseManager()

    if db_manager.initialize_database():
        print("[OK] Multi-site database initialized successfully")

        # Add initial site configurations
        initial_sites = [
            {
                'site_name': 'RockAuto',
                'base_url': 'https://www.rockauto.com',
                'is_active': True,
                'rate_limit_delay': 2.0,
                'max_retries': 3,
                'timeout_seconds': 30
            },
            {
                'site_name': 'PartsGeek',
                'base_url': 'https://www.partsgeek.com',
                'is_active': True,
                'rate_limit_delay': 3.0,
                'max_retries': 3,
                'timeout_seconds': 30
            },
            {
                'site_name': 'ACDelco',
                'base_url': 'https://www.acdelco.com',
                'is_active': True,
                'rate_limit_delay': 2.5,
                'max_retries': 3,
                'timeout_seconds': 30
            },
            {
                'site_name': 'Dorman',
                'base_url': 'https://www.dormanproducts.com',
                'is_active': True,
                'rate_limit_delay': 2.0,
                'max_retries': 3,
                'timeout_seconds': 30
            },
            {
                'site_name': 'Moog',
                'base_url': 'https://www.moogparts.com',
                'is_active': True,
                'rate_limit_delay': 2.0,
                'max_retries': 3,
                'timeout_seconds': 30
            },
            {
                'site_name': 'ShowMeTheParts',
                'base_url': 'https://www.showmetheparts.com',
                'is_active': False,  # Requires stealth bypass - not yet tested
                'rate_limit_delay': 3.0,
                'max_retries': 2,
                'timeout_seconds': 30,
                'status': 'blocked',
                'notes': 'Requires Incapsula WAF stealth bypass - 446-line scraper exists at src/scrapers/showmetheparts_scraper.py'
            }
        ]

        # Insert initial site configs
        for site in initial_sites:
            fields = ', '.join(site.keys())
            placeholders = ', '.join(['?' for _ in site.keys()])
            query = f"INSERT OR REPLACE INTO site_configs ({fields}) VALUES ({placeholders})"
            db_manager.execute_query(query, tuple(site.values()))

        print(f"[OK] Added {len(initial_sites)} site configurations")

        # Display database info
        info = db_manager.get_database_info()
        print(f"STATS: Database info:")
        print(f"   Path: {info['database_path']}")
        print(f"   Size: {info['database_size']:,} bytes")
        print(f"   Tables: {len(info['tables'])}")

        return db_manager
    else:
        print("[ERROR] Failed to initialize multi-site database")
        return None


if __name__ == "__main__":
    # Initialize database when run directly
    initialize_multi_site_database()