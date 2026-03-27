"""
Individual Chrome worker session for parallel scraping.

Manages a single Chrome browser instance with robust error handling,
health monitoring, and automatic recovery capabilities.
"""

import re
import time
import subprocess
import threading
from pathlib import Path
from typing import Dict, Optional
import logging
import tempfile

logger = logging.getLogger(__name__)

class ChromeWorker:
    """Individual Chrome browser worker for parallel scraping."""

    def __init__(self, worker_id: str, profile_dir: str):
        self.worker_id = worker_id
        self.profile_dir = profile_dir
        self.search_url = "https://www.rockauto.com/en/partsearch/"
        self.search_wait = 3000  # Reduced from 7000ms for better performance
        self.captcha_wait = 30   # Reduced timeout for parallel processing

        # Playwright components
        self._pw = None
        self._context = None
        self._page = None
        self._lock = threading.Lock()

        # Health tracking
        self._is_healthy = True
        self._last_health_check = 0
        self._consecutive_failures = 0
        self._max_consecutive_failures = 3

        logger.debug(f"ChromeWorker {worker_id} initialized with profile: {profile_dir}")

    def initialize(self) -> bool:
        """Initialize the Chrome browser session."""
        try:
            with self._lock:
                self._cleanup_existing()
                return self._launch_browser()
        except Exception as e:
            logger.error(f"Worker {self.worker_id} initialization failed: {e}")
            return False

    def _cleanup_existing(self):
        """Clean up any existing browser session."""
        try:
            if self._page:
                self._page.close()
            if self._context:
                self._context.close()
            if self._pw:
                self._pw.stop()
        except Exception as e:
            logger.debug(f"Worker {self.worker_id} cleanup warning: {e}")
        finally:
            self._page = None
            self._context = None
            self._pw = None

    def _launch_browser(self) -> bool:
        """Launch Chrome browser with optimal settings for parallel processing."""
        try:
            from playwright.sync_api import sync_playwright
            import playwright_stealth

            # Ensure profile directory exists
            Path(self.profile_dir).mkdir(parents=True, exist_ok=True)

            self._pw = sync_playwright().start()

            # Optimized Chrome args for parallel processing (without user-data-dir)
            chrome_args = [
                "--window-position=-2000,-2000",  # Off-screen
                "--window-size=1280,720",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-background-timer-throttling",
                "--disable-backgrounding-occluded-windows",
                "--disable-renderer-backgrounding",
                "--disable-features=TranslateUI",
                "--disable-component-extensions-with-background-pages",
                "--disable-ipc-flooding-protection",
                # Performance optimizations for parallel use
                "--max-active-webgl-contexts=1",
                "--disable-background-mode",
                "--disable-extensions",
                "--disable-plugins",
                "--disable-sync",
            ]

            self._context = self._pw.chromium.launch_persistent_context(
                user_data_dir=self.profile_dir,  # Correct parameter usage
                channel="chrome",  # Use real Chrome, not Chromium
                headless=False,    # Visible but off-screen
                args=chrome_args,  # Don't include user-data-dir in args
                ignore_default_args=["--enable-automation"],
                slow_mo=0,  # No artificial delays for parallel processing
            )

            # Apply stealth patches
            self._page = self._context.new_page()
            try:
                # Try different stealth function names
                if hasattr(playwright_stealth, 'stealth_sync'):
                    playwright_stealth.stealth_sync(self._page)
                elif hasattr(playwright_stealth, 'stealth'):
                    playwright_stealth.stealth(self._page)
                else:
                    logger.warning(f"Worker {self.worker_id}: stealth patches not available")
            except Exception as e:
                logger.warning(f"Worker {self.worker_id}: stealth patches failed: {e}")

            # Optimize page settings
            self._page.set_default_timeout(30000)  # 30s timeout
            self._page.set_default_navigation_timeout(30000)

            logger.info(f"Worker {self.worker_id} Chrome browser launched successfully")
            self._is_healthy = True
            self._consecutive_failures = 0
            return True

        except Exception as e:
            logger.error(f"Worker {self.worker_id} failed to launch browser: {e}")
            self._cleanup_existing()
            return False

    def health_check(self) -> bool:
        """Perform health check on the browser session."""
        try:
            with self._lock:
                if not self._page:
                    return False

                # Simple health check - verify page is responsive
                current_time = time.time()
                if current_time - self._last_health_check < 30:  # Don't check too frequently
                    return self._is_healthy

                # Quick responsiveness check
                self._page.evaluate("1 + 1")  # Simple JS execution
                self._last_health_check = current_time
                self._is_healthy = True
                logger.debug(f"Worker {self.worker_id} passed health check")
                return True

        except Exception as e:
            logger.warning(f"Worker {self.worker_id} failed health check: {e}")
            self._is_healthy = False
            return False

    def scrape_rockauto(self, part_number: str, brand: str) -> Dict:
        """
        Scrape RockAuto for a single part.
        Thread-safe implementation with robust error handling.
        """
        with self._lock:
            try:
                if not self._is_healthy:
                    raise Exception("Worker is not healthy")

                logger.debug(f"Worker {self.worker_id} scraping {brand} {part_number}")

                # Navigate to search page
                response = self._page.goto(self.search_url, wait_until="domcontentloaded")
                if not response or response.status >= 400:
                    raise Exception(f"Failed to load search page: {response.status if response else 'No response'}")

                # Fill search form
                self._page.fill("#partnum_partsearch_007", part_number)
                self._page.click("input[type='submit'][value='Search']")

                # Wait for results with reduced timeout for parallel processing
                self._page.wait_for_timeout(self.search_wait)

                # Check for CAPTCHA
                if self._page.locator("text=Please complete the security check").is_visible():
                    logger.warning(f"Worker {self.worker_id} hit CAPTCHA - waiting briefly")
                    self._page.wait_for_timeout(self.captcha_wait * 1000)

                    # If still CAPTCHA, fail this request
                    if self._page.locator("text=Please complete the security check").is_visible():
                        raise Exception("CAPTCHA detected - manual intervention required")

                # Find brand-specific results
                brand_results = self._find_brand_results(brand)
                if not brand_results:
                    return self._create_not_found_result(f"{brand} brand not found for part {part_number}")

                # Extract detailed information
                result = self._extract_part_details(brand_results[0], part_number, brand)

                # Reset failure count on success
                self._consecutive_failures = 0
                logger.debug(f"Worker {self.worker_id} successfully scraped {brand} {part_number}")

                return result

            except Exception as e:
                self._consecutive_failures += 1
                logger.error(f"Worker {self.worker_id} scraping failed (failure #{self._consecutive_failures}): {e}")

                # Mark as unhealthy if too many consecutive failures
                if self._consecutive_failures >= self._max_consecutive_failures:
                    self._is_healthy = False
                    logger.warning(f"Worker {self.worker_id} marked unhealthy after {self._consecutive_failures} failures")

                return self._create_error_result(str(e))

    def _find_brand_results(self, brand: str) -> list:
        """Find results for the specific brand."""
        try:
            # Look for "More Info" links
            moreinfo_links = self._page.locator("a[href*='moreinfo.php']").all()

            brand_results = []
            for link in moreinfo_links[:10]:  # Limit to first 10 for performance
                try:
                    # Get the parent element containing brand info
                    parent = link.locator("../..")
                    text_content = parent.inner_text().upper()

                    if brand.upper() in text_content:
                        brand_results.append({
                            'link': link,
                            'href': link.get_attribute('href'),
                            'text': text_content
                        })

                except Exception as e:
                    logger.debug(f"Worker {self.worker_id} error processing link: {e}")

            return brand_results

        except Exception as e:
            logger.error(f"Worker {self.worker_id} error finding brand results: {e}")
            return []

    def _extract_part_details(self, brand_result: Dict, part_number: str, brand: str) -> Dict:
        """Extract detailed part information."""
        try:
            moreinfo_url = brand_result['href']
            if not moreinfo_url.startswith('http'):
                moreinfo_url = f"https://www.rockauto.com{moreinfo_url}"

            # Navigate to detail page
            self._page.goto(moreinfo_url, wait_until="domcontentloaded")

            # Extract basic information
            result = {
                "part_number": part_number,
                "brand": brand,
                "found": True,
                "moreinfo_url": moreinfo_url,
                "error": None
            }

            # Extract category
            try:
                title_element = self._page.locator("title")
                if title_element.is_visible():
                    title = title_element.inner_text()
                    # Extract category from title
                    if " | " in title:
                        category = title.split(" | ")[1].strip()
                        result["category"] = category
                else:
                    result["category"] = None
            except:
                result["category"] = None

            # Extract OEM references
            result["oem_refs"] = self._extract_oem_refs()

            # Extract price
            result["price"] = self._extract_price()

            # Extract description and features
            result["description"] = self._extract_description()
            result["features"] = self._extract_features()

            # Extract specifications
            result["specs"] = self._extract_specs()

            # Extract warranty info
            result["warranty"] = self._extract_warranty()

            # Extract image URL
            result["image_url"] = self._extract_image_url()

            return result

        except Exception as e:
            logger.error(f"Worker {self.worker_id} error extracting details: {e}")
            return self._create_error_result(f"Failed to extract details: {e}")

    def _extract_oem_refs(self) -> list:
        """Extract OEM/interchange numbers from the page."""
        oem_refs = []
        try:
            # Look for OEM/Interchange section
            page_text = self._page.content()

            # Pattern for OEM numbers
            oem_patterns = [
                r'OEM\s*/?:?\s*([A-Z0-9\-,\s]+)',
                r'Interchange\s*/?:?\s*([A-Z0-9\-,\s]+)',
                r'OEM\s*/?\s*Interchange\s*Numbers?\s*:?\s*([A-Z0-9\-,\s]+)'
            ]

            for pattern in oem_patterns:
                matches = re.finditer(pattern, page_text, re.IGNORECASE)
                for match in matches:
                    refs_text = match.group(1)
                    # Split and clean OEM references
                    refs = [ref.strip() for ref in re.split(r'[,\s]+', refs_text) if ref.strip()]
                    oem_refs.extend(refs)

            # Remove duplicates and filter valid OEM numbers
            seen = set()
            filtered_refs = []
            for ref in oem_refs:
                if ref and len(ref) > 3 and ref not in seen:
                    seen.add(ref)
                    filtered_refs.append(ref)

            return filtered_refs[:10]  # Limit to 10 OEM refs

        except Exception as e:
            logger.debug(f"Worker {self.worker_id} error extracting OEM refs: {e}")
            return []

    def _extract_price(self) -> Optional[str]:
        """Extract price information."""
        try:
            # Look for price patterns
            price_selectors = [
                ".price",
                "[class*='price']",
                "text=/\\$[0-9]+\\.[0-9]{2}/"
            ]

            for selector in price_selectors:
                try:
                    price_element = self._page.locator(selector).first
                    if price_element.is_visible():
                        price_text = price_element.inner_text()
                        # Extract price with regex
                        price_match = re.search(r'\$([0-9]+\.[0-9]{2})', price_text)
                        if price_match:
                            return f"${price_match.group(1)}"
                except:
                    continue

            return None

        except Exception as e:
            logger.debug(f"Worker {self.worker_id} error extracting price: {e}")
            return None

    def _extract_description(self) -> Optional[str]:
        """Extract part description."""
        try:
            # Look for description in various locations
            desc_selectors = [
                ".description",
                "[class*='description']",
                "h1",
                "title"
            ]

            for selector in desc_selectors:
                try:
                    desc_element = self._page.locator(selector).first
                    if desc_element.is_visible():
                        desc = desc_element.inner_text().strip()
                        if len(desc) > 5:
                            return desc[:500]  # Limit length
                except:
                    continue

            return None

        except Exception as e:
            logger.debug(f"Worker {self.worker_id} error extracting description: {e}")
            return None

    def _extract_features(self) -> list:
        """Extract part features."""
        try:
            features = []
            # Look for feature lists
            feature_elements = self._page.locator("ul li, .feature, [class*='feature']").all()

            for element in feature_elements[:10]:  # Limit to 10 features
                try:
                    text = element.inner_text().strip()
                    if text and len(text) > 5 and len(text) < 100:
                        features.append(text)
                except:
                    continue

            return features

        except Exception as e:
            logger.debug(f"Worker {self.worker_id} error extracting features: {e}")
            return []

    def _extract_specs(self) -> Optional[Dict]:
        """Extract specifications."""
        try:
            specs = {}
            # Look for specification tables or lists
            spec_elements = self._page.locator("table tr, .spec, [class*='spec']").all()

            for element in spec_elements[:20]:  # Limit to 20 specs
                try:
                    text = element.inner_text().strip()
                    if ':' in text:
                        parts = text.split(':', 1)
                        if len(parts) == 2:
                            key = parts[0].strip()
                            value = parts[1].strip()
                            if key and value:
                                specs[key] = value
                except:
                    continue

            return specs if specs else None

        except Exception as e:
            logger.debug(f"Worker {self.worker_id} error extracting specs: {e}")
            return None

    def _extract_warranty(self) -> Optional[str]:
        """Extract warranty information."""
        try:
            warranty_selectors = [
                "text=/warranty/i",
                ".warranty",
                "[class*='warranty']"
            ]

            for selector in warranty_selectors:
                try:
                    warranty_element = self._page.locator(selector).first
                    if warranty_element.is_visible():
                        warranty_text = warranty_element.inner_text().strip()
                        if len(warranty_text) > 5:
                            return warranty_text[:200]  # Limit length
                except:
                    continue

            return None

        except Exception as e:
            logger.debug(f"Worker {self.worker_id} error extracting warranty: {e}")
            return None

    def _extract_image_url(self) -> Optional[str]:
        """Extract product image URL."""
        try:
            # Look for product images
            img_selectors = [
                "img[src*='/info/']",
                "img[src*='product']",
                ".product-image img",
                "[class*='image'] img"
            ]

            for selector in img_selectors:
                try:
                    img_element = self._page.locator(selector).first
                    if img_element.is_visible():
                        src = img_element.get_attribute('src')
                        if src and '/info/' in src:
                            if src.startswith('//'):
                                src = f"https:{src}"
                            elif src.startswith('/'):
                                src = f"https://www.rockauto.com{src}"
                            return src
                except:
                    continue

            return None

        except Exception as e:
            logger.debug(f"Worker {self.worker_id} error extracting image URL: {e}")
            return None

    def _create_not_found_result(self, reason: str) -> Dict:
        """Create a standardized not-found result."""
        return {
            "found": False,
            "error": reason,
            "category": None,
            "oem_refs": [],
            "price": None,
            "moreinfo_url": None,
            "image_url": None,
            "specs": None,
            "description": None,
            "features": None,
            "warranty": None
        }

    def _create_error_result(self, error_message: str) -> Dict:
        """Create a standardized error result."""
        return {
            "found": False,
            "error": error_message,
            "category": None,
            "oem_refs": [],
            "price": None,
            "moreinfo_url": None,
            "image_url": None,
            "specs": None,
            "description": None,
            "features": None,
            "warranty": None
        }

    def cleanup(self):
        """Clean up the Chrome worker session."""
        try:
            with self._lock:
                self._cleanup_existing()

                # Clean up profile directory
                try:
                    import shutil
                    if Path(self.profile_dir).exists():
                        shutil.rmtree(self.profile_dir, ignore_errors=True)
                except Exception as e:
                    logger.debug(f"Worker {self.worker_id} profile cleanup warning: {e}")

                logger.info(f"ChromeWorker {self.worker_id} cleaned up")

        except Exception as e:
            logger.error(f"Worker {self.worker_id} cleanup error: {e}")

    def __del__(self):
        """Destructor to ensure cleanup."""
        try:
            self.cleanup()
        except:
            pass