#!/usr/bin/env python3
"""
Multi-Site Scraper Manager
Coordinates scraping across multiple auto parts sites
Integrates with existing Chrome/Playwright infrastructure
"""

import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import sys
import json

# Unicode safety utilities
sys.path.insert(0, str(Path(__file__).parent.parent))
from unicode_utils import sanitize_unicode_dict, sanitize_unicode_text

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.db_manager import DatabaseManager
from scraper_subprocess import scrape_rockauto_subprocess


class MultiSiteScraperManager:
    """Manages scraping across multiple auto parts sites"""

    def __init__(self, db_manager: DatabaseManager = None):
        """Initialize multi-site scraper manager

        Args:
            db_manager: Optional database manager instance
        """
        self.db_manager = db_manager or DatabaseManager()
        self.logger = logging.getLogger(__name__)

        # Initialize database if needed
        self.db_manager.initialize_database()

        # Site-specific scrapers registry
        self.scrapers = {
            'RockAuto': self._scrape_rockauto,
            'PartsGeek': self._scrape_partsgeek,
            'ACDelco': self._scrape_acdelco,
            'Dorman': self._scrape_dorman,
            'Moog': self._scrape_moog,
            'ShowMeTheParts': self._scrape_showmetheparts  # Stealth scraper for Incapsula bypass
        }

        # Load site configurations
        self.site_configs = self._load_site_configs()

    def _load_site_configs(self) -> Dict[str, Dict]:
        """Load site configurations from database

        Returns:
            Dict: Site configurations keyed by site name
        """
        configs = {}
        site_list = self.db_manager.get_site_configs()

        for site in site_list:
            configs[site['site_name']] = site

        self.logger.info(f"Loaded {len(configs)} site configurations")
        return configs

    def scrape_part_multi_site(self, part_number: str, brand: str,
                              sites: List[str] = None, store_results: bool = True) -> Dict[str, Any]:
        """Scrape a part across multiple sites

        Args:
            part_number: Part number to search
            brand: Brand name
            sites: List of sites to scrape (default: all active sites)
            store_results: Whether to store results in database

        Returns:
            Dict: Results from all sites
        """
        if sites is None:
            sites = [name for name, config in self.site_configs.items()
                    if config.get('is_active', False)]

        results = {
            'part_number': part_number,
            'brand': brand,
            'timestamp': datetime.now().isoformat(),
            'sites': {},
            'summary': {
                'total_sites': len(sites),
                'successful_sites': 0,
                'failed_sites': 0,
                'found_on_sites': 0,
                'total_sources': 0
            }
        }

        # Get or create part in database
        part_id = None
        if store_results:
            part_id = self.db_manager.add_part(part_number, brand)
            if part_id is None:
                # Part might already exist, get it
                existing_part = self.db_manager.get_part_by_number(part_number, brand)
                part_id = existing_part['id'] if existing_part else None

        # Scrape each site
        for site_name in sites:
            if site_name not in self.site_configs:
                self.logger.warning(f"Site {site_name} not found in configurations")
                continue

            config = self.site_configs[site_name]
            if not config.get('is_active', False):
                self.logger.info(f"Skipping inactive site: {site_name}")
                continue

            try:
                # Add rate limiting delay
                if config.get('rate_limit_delay', 0) > 0:
                    time.sleep(config['rate_limit_delay'])

                # Scrape the site
                site_result = self._scrape_site(site_name, part_number, brand, config)

                results['sites'][site_name] = site_result

                # Update summary
                if site_result.get('success', False):
                    results['summary']['successful_sites'] += 1
                    if site_result.get('found', False):
                        results['summary']['found_on_sites'] += 1

                        # Store in database
                        if store_results and part_id:
                            self._store_site_result(part_id, site_name, site_result)

                else:
                    results['summary']['failed_sites'] += 1

            except Exception as e:
                self.logger.error(f"Error scraping {site_name}: {e}")
                results['sites'][site_name] = {
                    'success': False,
                    'found': False,
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }
                results['summary']['failed_sites'] += 1

        # Log scraping activity
        if store_results:
            self._log_multi_site_activity(part_number, results)

        return results

    def _scrape_site(self, site_name: str, part_number: str, brand: str,
                    config: Dict) -> Dict[str, Any]:
        """Scrape a specific site

        Args:
            site_name: Name of site to scrape
            part_number: Part number to search
            brand: Brand name
            config: Site configuration

        Returns:
            Dict: Scraping results
        """
        if site_name not in self.scrapers:
            raise ValueError(f"No scraper available for site: {site_name}")

        start_time = time.time()
        try:
            result = self.scrapers[site_name](part_number, brand, config)
            result['duration'] = time.time() - start_time
            result['timestamp'] = datetime.now().isoformat()
            return result
        except Exception as e:
            return {
                'success': False,
                'found': False,
                'error': str(e),
                'duration': time.time() - start_time,
                'timestamp': datetime.now().isoformat()
            }

    def _scrape_rockauto(self, part_number: str, brand: str, config: Dict) -> Dict[str, Any]:
        """Scrape RockAuto using existing infrastructure

        Args:
            part_number: Part number to search
            brand: Brand name
            config: Site configuration

        Returns:
            Dict: Scraping results
        """
        try:
            # Use existing RockAuto scraper
            result = scrape_rockauto_subprocess(part_number, brand)

            # Standardize result format
            standardized = {
                'success': not result.get('blocked', False),
                'found': result.get('found', False),
                'site_name': 'RockAuto',
                'part_number': part_number,
                'brand': brand,
                'category': result.get('category'),
                'oem_refs': result.get('oem_refs', []),
                'price': result.get('price'),
                'image_url': result.get('image_url'),
                'product_url': result.get('moreinfo_url'),
                'description': result.get('description'),
                'specs': result.get('specs', {}),
                'features': result.get('features', []),
                'availability': None,  # Not provided by current scraper
                'stock_quantity': None,
                'error': result.get('error')
            }

            return standardized

        except Exception as e:
            return {
                'success': False,
                'found': False,
                'error': str(e),
                'site_name': 'RockAuto'
            }

    def _scrape_partsgeek(self, part_number: str, brand: str, config: Dict) -> Dict[str, Any]:
        """Scrape PartsGeek using dedicated PartsGeek scraper

        Args:
            part_number: Part number to search
            brand: Brand name
            config: Site configuration

        Returns:
            Dict: Scraping results
        """
        try:
            from scrapers.partsgeek_scraper import PartsGeekScraper

            scraper = PartsGeekScraper(headless=False)
            result = scraper.scrape_part(part_number, brand, config)

            return result

        except Exception as e:
            return {
                'success': False,
                'found': False,
                'error': f'PartsGeek scraper error: {str(e)}',
                'site_name': 'PartsGeek'
            }

    def _scrape_acdelco(self, part_number: str, brand: str, config: Dict) -> Dict[str, Any]:
        """Scrape ACDelco using dedicated ACDelco scraper

        Args:
            part_number: Part number to search
            brand: Brand name
            config: Site configuration

        Returns:
            Dict: Scraping results
        """
        try:
            from scrapers.acdelco_scraper import ACDelcoScraper

            # Initialize scraper (non-headless for better compatibility)
            scraper = ACDelcoScraper(headless=False)

            # Scrape the part
            result = scraper.scrape_part(part_number, brand, config)

            # Standardize result format (ACDelco scraper already returns standardized format)
            standardized = {
                'success': result.get('success', False),
                'found': result.get('found', False),
                'site_name': 'ACDelco',
                'part_number': part_number,
                'brand': result.get('brand', brand),
                'category': result.get('category'),
                'oem_refs': result.get('oem_refs', []),
                'price': result.get('price'),
                'image_url': result.get('image_url'),
                'product_url': result.get('product_url'),
                'description': result.get('description'),
                'specs': result.get('specs', {}),
                'features': result.get('features', []),
                'availability': result.get('availability'),
                'stock_quantity': result.get('stock_quantity'),
                'fitment_data': result.get('fitment_data', []),  # Critical for fitment table
                'error': result.get('error')
            }

            return standardized

        except Exception as e:
            return {
                'success': False,
                'found': False,
                'error': f'ACDelco scraper error: {str(e)}',
                'site_name': 'ACDelco'
            }

    def _scrape_dorman(self, part_number: str, brand: str, config: Dict) -> Dict[str, Any]:
        """Scrape Dorman Products (placeholder - to be implemented)

        Args:
            part_number: Part number to search
            brand: Brand name
            config: Site configuration

        Returns:
            Dict: Scraping results
        """
        # TODO: Implement Dorman scraper using Chrome/Playwright
        return {
            'success': False,
            'found': False,
            'error': 'Dorman scraper not yet implemented',
            'site_name': 'Dorman'
        }

    def _scrape_moog(self, part_number: str, brand: str, config: Dict) -> Dict[str, Any]:
        """Scrape Moog Parts (placeholder - to be implemented)

        Args:
            part_number: Part number to search
            brand: Brand name
            config: Site configuration

        Returns:
            Dict: Scraping results
        """
        # TODO: Implement Moog scraper using Chrome/Playwright
        return {
            'success': False,
            'found': False,
            'error': 'Moog scraper not yet implemented',
            'site_name': 'Moog'
        }

    def _scrape_showmetheparts(self, part_number: str, brand: str, config: Dict) -> Dict[str, Any]:
        """Scrape ShowMeTheParts using stealth techniques to bypass Incapsula WAF

        Args:
            part_number: Part number to search
            brand: Brand name
            config: Site configuration

        Returns:
            Dict: Scraping results
        """
        try:
            from scrapers.showmetheparts_scraper import ShowMeThePartsScraper

            scraper = ShowMeThePartsScraper(headless=False)
            result = scraper.scrape_part(part_number, brand)

            return result

        except Exception as e:
            return {
                'success': False,
                'found': False,
                'error': f'ShowMeTheParts scraper error: {str(e)}',
                'site_name': 'ShowMeTheParts'
            }

    def _store_site_result(self, part_id: int, site_name: str, result: Dict) -> bool:
        """Store scraping result in database

        Args:
            part_id: Part ID from database
            site_name: Name of scraped site
            result: Scraping result data

        Returns:
            bool: True if stored successfully
        """
        try:
            # Apply Unicode sanitization to prevent database storage crashes
            try:
                result = sanitize_unicode_dict(result)
                site_name = sanitize_unicode_text(site_name)
            except Exception as e:
                self.logger.error(f"Unicode sanitization failed: {e}")
                # Continue with original data if sanitization fails

            # Update parts.category and part_name if currently NULL
            if result.get('category') or result.get('description'):
                self.db_manager.execute_query(
                    """UPDATE parts SET
                       category = COALESCE(category, ?),
                       part_name = COALESCE(part_name, ?),
                       updated_at = CURRENT_TIMESTAMP
                       WHERE id = ?""",
                    (result.get('category'), result.get('description'), part_id)
                )

            # Handle multiple listings per part (new approach)
            listings = result.get('listings', [result])  # Backward compatibility
            success = False
            for listing in listings:
                listing_success = self.db_manager.add_part_source(
                    part_id=part_id,
                    site_name=site_name,
                    listing_id=listing.get('listing_id'),
                    availability_status=listing.get('availability') or listing.get('availability_status'),
                    price=self._parse_price(listing.get('price')),
                    core_charge=self._parse_price(listing.get('core_charge')),
                    stock_quantity=listing.get('stock_quantity'),
                    product_url=listing.get('product_url') or listing.get('moreinfo_url'),
                    scrape_success=listing.get('success', listing.get('found', False)),
                    scrape_error=listing.get('error')
                )
                if listing_success:
                    success = True

            # Store OEM references if available
            if result.get('oem_refs') and success:
                for oem_ref in result['oem_refs']:
                    # Handle both old string format and new dict format
                    if isinstance(oem_ref, dict):
                        ref_number = oem_ref.get('oem_number')
                        ref_type = oem_ref.get('reference_type', 'OEM')
                        ref_brand = oem_ref.get('oem_brand')
                    else:
                        ref_number = oem_ref
                        ref_type = 'OEM'
                        ref_brand = None

                    if ref_number:
                        self.db_manager.execute_query(
                            """INSERT OR IGNORE INTO oem_references
                               (part_id, oem_number, oem_brand, source_site, confidence, reference_type)
                               VALUES (?, ?, ?, ?, ?, ?)""",
                            (part_id, ref_number, ref_brand, site_name, 1.0, ref_type)
                        )

            # Store image URL if available
            if result.get('image_url') and success:
                self.db_manager.execute_query(
                    """INSERT OR IGNORE INTO part_images
                       (part_id, site_name, image_url, image_type, is_primary)
                       VALUES (?, ?, ?, ?, ?)""",
                    (part_id, site_name, result['image_url'], 'product', True)
                )

            # Store specifications if available
            if result.get('specs') and success:
                for spec_name, spec_value in result['specs'].items():
                    if spec_value:
                        self.db_manager.execute_query(
                            """INSERT OR IGNORE INTO part_specs
                               (part_id, site_name, spec_name, spec_value)
                               VALUES (?, ?, ?, ?)""",
                            (part_id, site_name, spec_name, str(spec_value))
                        )

            # Store fitment data if available (CRITICAL for fitment table population)
            if result.get('fitment_data') and success:
                for fitment in result['fitment_data']:
                    if (fitment.get('year') or fitment.get('year_start')) and fitment.get('make') and fitment.get('model'):
                        if fitment.get('year_start'):
                            yr_start = fitment['year_start']
                            yr_end = fitment.get('year_end', fitment['year_start'])
                        else:
                            yr_start = fitment['year']
                            yr_end = fitment['year']
                        self.db_manager.execute_query(
                            """INSERT OR IGNORE INTO fitment
                               (part_id, year_start, year_end, make, model, engine, source_site, confidence)
                               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                            (part_id, yr_start, yr_end, fitment['make'],
                             fitment['model'], fitment.get('engine'), site_name, 1.0)
                        )

            return success

        except Exception as e:
            self.logger.error(f"Failed to store site result: {e}")
            return False

    def _extract_fitment_from_url(self, url: str) -> dict:
        """Extract vehicle fitment from RockAuto catalog URL"""
        try:
            if '/catalog/' in url:
                path_parts = url.split('/catalog/')[-1].split(',')
                if len(path_parts) >= 4:
                    return {
                        "make": path_parts[0].replace('+', ' ').title(),
                        "year": int(path_parts[1]) if path_parts[1].isdigit() else None,
                        "model": path_parts[2].replace('+', ' ').title(),
                        "engine": path_parts[3].replace('+', ' ').upper() if len(path_parts) > 3 else None
                    }
        except Exception:
            pass
        return {}

    def _parse_price(self, price_str: str) -> Optional[float]:
        """Parse price string to float

        Args:
            price_str: Price string (e.g., "$25.99")

        Returns:
            float: Parsed price or None
        """
        if not price_str:
            return None

        try:
            # Remove currency symbols and whitespace
            clean_price = price_str.replace('$', '').replace(',', '').strip()
            return float(clean_price)
        except (ValueError, AttributeError):
            return None

    def _log_multi_site_activity(self, search_term: str, results: Dict) -> None:
        """Log multi-site scraping activity

        Args:
            search_term: Search term used
            results: Complete scraping results
        """
        summary = results['summary']

        # Log overall activity
        self.db_manager.add_scrape_log(
            site_name='MultiSite',
            scrape_type='multi_search',
            search_term=search_term,
            success=summary['successful_sites'] > 0,
            rows_collected=summary['found_on_sites'],
            rows_failed=summary['failed_sites'],
            user_agent='Parts Agent Multi-Site Manager'
        )

        # Log individual site activities
        for site_name, site_result in results['sites'].items():
            if 'duration' in site_result:
                self.db_manager.add_scrape_log(
                    site_name=site_name,
                    scrape_type='search',
                    search_term=search_term,
                    success=site_result.get('success', False),
                    rows_collected=1 if site_result.get('found', False) else 0,
                    duration_seconds=site_result.get('duration'),
                    error_message=site_result.get('error'),
                    user_agent='Parts Agent Multi-Site Manager'
                )

    def get_multi_site_summary(self, part_number: str, brand: str) -> Dict[str, Any]:
        """Get summary of part data across all sites

        Args:
            part_number: Part number to summarize
            brand: Brand name

        Returns:
            Dict: Summary of part across all sites
        """
        # Get part from database
        part = self.db_manager.get_part_by_number(part_number, brand)
        if not part:
            return {'error': 'Part not found in database'}

        # Get all sources for this part
        sources_query = """
            SELECT * FROM part_sources
            WHERE part_id = ?
            ORDER BY site_name
        """
        sources = self.db_manager.execute_query(sources_query, (part['id'],), fetch='all')

        # Get OEM references
        oem_query = """
            SELECT oem_number, oem_brand, source_site
            FROM oem_references
            WHERE part_id = ?
        """
        oem_refs = self.db_manager.execute_query(oem_query, (part['id'],), fetch='all')

        # Get images
        images_query = """
            SELECT image_url, site_name, image_type
            FROM part_images
            WHERE part_id = ?
        """
        images = self.db_manager.execute_query(images_query, (part['id'],), fetch='all')

        summary = {
            'part_info': dict(part),
            'sites_found': len([s for s in sources if s['scrape_success']]),
            'total_sites_checked': len(sources),
            'price_range': self._calculate_price_range([dict(s) for s in sources]),
            'sources': [dict(s) for s in sources],
            'oem_references': [dict(o) for o in oem_refs] if oem_refs else [],
            'images': [dict(i) for i in images] if images else [],
            'availability_summary': self._summarize_availability([dict(s) for s in sources])
        }

        return summary

    def _calculate_price_range(self, sources: List[Dict]) -> Dict[str, Any]:
        """Calculate price range from sources

        Args:
            sources: List of source dictionaries

        Returns:
            Dict: Price range information
        """
        prices = [s['price'] for s in sources if s.get('price')]
        if not prices:
            return {'min': None, 'max': None, 'count': 0}

        return {
            'min': min(prices),
            'max': max(prices),
            'average': sum(prices) / len(prices),
            'count': len(prices)
        }

    def _summarize_availability(self, sources: List[Dict]) -> Dict[str, int]:
        """Summarize availability across sources

        Args:
            sources: List of source dictionaries

        Returns:
            Dict: Availability summary
        """
        summary = {}
        for source in sources:
            status = source.get('availability_status', 'Unknown')
            summary[status] = summary.get(status, 0) + 1
        return summary


def test_multi_site_scraper():
    """Test multi-site scraper with known part"""
    print(">> Testing Multi-Site Scraper")
    print("=" * 50)

    manager = MultiSiteScraperManager()

    # Test with known working part
    test_part = "3217"
    test_brand = "ANCHOR"

    print(f"Testing part: {test_brand} {test_part}")

    # Scrape across sites (currently only RockAuto implemented)
    results = manager.scrape_part_multi_site(
        part_number=test_part,
        brand=test_brand,
        sites=['RockAuto'],  # Only test implemented scraper
        store_results=True
    )

    print("\nResults:")
    print(f"Total sites: {results['summary']['total_sites']}")
    print(f"Successful: {results['summary']['successful_sites']}")
    print(f"Found on: {results['summary']['found_on_sites']} sites")

    for site, site_result in results['sites'].items():
        print(f"\n{site}:")
        print(f"  Success: {site_result.get('success', False)}")
        print(f"  Found: {site_result.get('found', False)}")
        if site_result.get('found'):
            print(f"  Category: {site_result.get('category')}")
            print(f"  Price: {site_result.get('price')}")
            print(f"  OEM Refs: {len(site_result.get('oem_refs', []))}")

    # Test summary
    print("\n>> Testing Multi-Site Summary")
    summary = manager.get_multi_site_summary(test_part, test_brand)
    if 'error' not in summary:
        print(f"Sites found on: {summary['sites_found']}")
        print(f"Price range: ${summary['price_range']['min']} - ${summary['price_range']['max']}")
        print(f"OEM references: {len(summary['oem_references'])}")

    print("\n[OK] Multi-site scraper test completed")


if __name__ == "__main__":
    # Test when run directly
    test_multi_site_scraper()