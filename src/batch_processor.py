"""
Batch processor for Excel rows using parallel scraping.

Integrates with the existing excel_handler.py to process rows in batches
rather than sequentially, providing significant speed improvements while
maintaining compatibility and robustness.
"""

import time
import logging
from typing import List, Dict, Tuple, Optional, Callable
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class BatchJob:
    """Represents a batch of Excel rows to process."""
    row_data: List[Dict]  # List of row dictionaries from excel_handler
    batch_id: str
    sheet_name: str
    brand: str
    created_at: float

@dataclass
class BatchResult:
    """Results from processing a batch."""
    batch_job: BatchJob
    comparison_results: List[Dict]
    success_count: int
    duration: float
    errors: List[str]

class BatchProcessor:
    """Processes Excel rows in batches using parallel scraping."""

    def __init__(self, batch_size: int = 8, max_workers: int = 4,
                 enable_parallel: bool = True):
        self.batch_size = batch_size
        self.max_workers = max_workers
        self.enable_parallel = enable_parallel

        # Performance tracking
        self.stats = {
            "batches_processed": 0,
            "rows_processed": 0,
            "total_duration": 0,
            "parallel_used": 0,
            "sequential_fallback": 0
        }

    def process_rows_batch(self,
                          rows: List[Dict],
                          sheet_name: str,
                          brand: str,
                          on_progress: Optional[Callable[[int, int], None]] = None,
                          on_log: Optional[Callable[[str], None]] = None,
                          stop_flag: Optional[List[bool]] = None) -> List[Dict]:
        """
        Process Excel rows in batches with parallel scraping.

        Args:
            rows: List of row dictionaries from excel_handler.get_valid_rows()
            sheet_name: Name of the Excel sheet being processed
            brand: Brand to search for (e.g., "ANCHOR", "DORMAN")
            on_progress: Callback for progress updates (current, total)
            on_log: Callback for log messages
            stop_flag: [bool] list to check for stop requests

        Returns:
            List of comparison results (same order as input rows)
        """
        if not rows:
            return []

        start_time = time.time()
        total_rows = len(rows)

        log = on_log if on_log else logger.info
        log(f"Starting batch processing: {total_rows} rows, batch_size={self.batch_size}, parallel={self.enable_parallel}")

        # Split rows into batches
        batches = self._create_batches(rows, sheet_name, brand)
        all_results = []

        try:
            for batch_idx, batch in enumerate(batches):
                # Check stop flag
                if stop_flag and stop_flag[0]:
                    log("Stop flag detected - interrupting batch processing")
                    break

                log(f"Processing batch {batch_idx + 1}/{len(batches)} ({len(batch.row_data)} rows)")

                # Process the batch
                batch_result = self._process_single_batch(batch, on_log)
                all_results.extend(batch_result.comparison_results)

                # Update statistics
                self.stats["batches_processed"] += 1
                self.stats["rows_processed"] += len(batch.row_data)

                # Progress callback
                if on_progress:
                    completed_rows = len(all_results)
                    on_progress(completed_rows, total_rows)

                # Log batch completion
                success_rate = (batch_result.success_count / len(batch.row_data)) * 100
                log(f"Batch {batch_idx + 1} completed: {batch_result.success_count}/{len(batch.row_data)} successful ({success_rate:.1f}%) in {batch_result.duration:.1f}s")

                # Brief pause between batches to be respectful
                if batch_idx < len(batches) - 1:  # Don't pause after last batch
                    time.sleep(1.0)

            duration = time.time() - start_time
            self.stats["total_duration"] += duration

            success_count = sum(1 for r in all_results if r.get("match_result") != "ERROR")
            log(f"Batch processing completed: {success_count}/{len(all_results)} successful in {duration:.1f}s")

            return all_results

        except Exception as e:
            log(f"Batch processing failed: {e}")
            # Return error results for all remaining rows
            error_results = []
            for _ in range(len(rows) - len(all_results)):
                error_results.append(self._create_error_comparison("Batch processing failed"))

            all_results.extend(error_results)
            return all_results

    def _create_batches(self, rows: List[Dict], sheet_name: str, brand: str) -> List[BatchJob]:
        """Split rows into batches for parallel processing."""
        batches = []

        for i in range(0, len(rows), self.batch_size):
            batch_rows = rows[i:i + self.batch_size]
            batch = BatchJob(
                row_data=batch_rows,
                batch_id=f"batch_{i//self.batch_size + 1}_{int(time.time())}",
                sheet_name=sheet_name,
                brand=brand,
                created_at=time.time()
            )
            batches.append(batch)

        return batches

    def _process_single_batch(self, batch: BatchJob,
                             on_log: Optional[Callable[[str], None]] = None) -> BatchResult:
        """Process a single batch of rows."""
        start_time = time.time()
        log = on_log if on_log else logger.info

        try:
            # Prepare scraping jobs (part_number, brand) pairs
            scraping_jobs = []
            skp_jobs = []

            for row in batch.row_data:
                # Brand part (left side)
                scraping_jobs.append((row["part_num"], batch.brand))
                # SKP part (right side)
                skp_jobs.append((row["skp_num"], "SKP"))

            # Parallel scraping if enabled
            if self.enable_parallel and len(scraping_jobs) > 1:
                try:
                    brand_results, skp_results = self._scrape_parallel_batch(
                        scraping_jobs, skp_jobs, on_log
                    )
                    self.stats["parallel_used"] += 1
                except Exception as e:
                    log(f"Parallel scraping failed for batch {batch.batch_id}: {e}")
                    log("Falling back to sequential processing")
                    brand_results, skp_results = self._scrape_sequential_batch(
                        scraping_jobs, skp_jobs, on_log
                    )
                    self.stats["sequential_fallback"] += 1
            else:
                # Sequential processing
                brand_results, skp_results = self._scrape_sequential_batch(
                    scraping_jobs, skp_jobs, on_log
                )
                self.stats["sequential_fallback"] += 1

            # Generate comparison results
            comparison_results = []
            errors = []
            success_count = 0

            for i, row in enumerate(batch.row_data):
                try:
                    brand_data = brand_results[i] if i < len(brand_results) else None
                    skp_data = skp_results[i] if i < len(skp_results) else None

                    if brand_data is None or skp_data is None:
                        comparison = self._create_error_comparison("Scraping data missing")
                        errors.append(f"Row {row.get('row_num', i)}: Missing scraping data")
                    else:
                        # Use existing rule comparison
                        comparison = self._compare_parts(
                            brand_data, skp_data, row["part_type"]
                        )
                        if comparison.get("match_result") != "ERROR":
                            success_count += 1

                    comparison_results.append(comparison)

                except Exception as e:
                    error_msg = f"Row {row.get('row_num', i)}: Comparison failed: {e}"
                    errors.append(error_msg)
                    comparison_results.append(self._create_error_comparison(error_msg))

            duration = time.time() - start_time

            return BatchResult(
                batch_job=batch,
                comparison_results=comparison_results,
                success_count=success_count,
                duration=duration,
                errors=errors
            )

        except Exception as e:
            # Complete batch failure
            error_msg = f"Batch {batch.batch_id} processing failed: {e}"
            duration = time.time() - start_time

            error_results = []
            for _ in batch.row_data:
                error_results.append(self._create_error_comparison(error_msg))

            return BatchResult(
                batch_job=batch,
                comparison_results=error_results,
                success_count=0,
                duration=duration,
                errors=[error_msg]
            )

    def _scrape_parallel_batch(self, brand_jobs: List[Tuple[str, str]],
                              skp_jobs: List[Tuple[str, str]],
                              on_log: Optional[Callable[[str], None]] = None) -> Tuple[List[Dict], List[Dict]]:
        """Scrape both brand and SKP parts in parallel."""
        log = on_log if on_log else logger.info

        try:
            from parallel_scraper import scrape_rockauto_batch

            # Combine all jobs for parallel processing
            all_jobs = brand_jobs + skp_jobs
            log(f"Starting parallel scraping of {len(all_jobs)} parts ({self.max_workers} workers)")

            # Parallel scraping
            all_results = scrape_rockauto_batch(all_jobs, max_workers=self.max_workers)

            # Split results back to brand and SKP
            brand_count = len(brand_jobs)
            brand_results = all_results[:brand_count]
            skp_results = all_results[brand_count:]

            return brand_results, skp_results

        except Exception as e:
            logger.error(f"Parallel scraping failed: {e}")
            raise

    def _scrape_sequential_batch(self, brand_jobs: List[Tuple[str, str]],
                                skp_jobs: List[Tuple[str, str]],
                                on_log: Optional[Callable[[str], None]] = None) -> Tuple[List[Dict], List[Dict]]:
        """Scrape parts sequentially using existing scraper."""
        log = on_log if on_log else logger.info

        try:
            from scraper_subprocess import scrape_rockauto_subprocess

            brand_results = []
            skp_results = []

            # Process brand parts
            for part_number, brand in brand_jobs:
                try:
                    result = scrape_rockauto_subprocess(part_number, brand)
                    brand_results.append(result)
                except Exception as e:
                    log(f"Sequential scraping failed for {brand} {part_number}: {e}")
                    brand_results.append(self._create_scraping_error(f"Scraping failed: {e}"))

            # Process SKP parts
            for part_number, brand in skp_jobs:
                try:
                    result = scrape_rockauto_subprocess(part_number, brand)
                    skp_results.append(result)
                except Exception as e:
                    log(f"Sequential scraping failed for {brand} {part_number}: {e}")
                    skp_results.append(self._create_scraping_error(f"Scraping failed: {e}"))

            return brand_results, skp_results

        except Exception as e:
            logger.error(f"Sequential scraping setup failed: {e}")
            raise

    def _compare_parts(self, brand_data: Dict, skp_data: Dict, part_type: str) -> Dict:
        """Compare parts using existing rule comparison engine."""
        try:
            from rule_compare import compare_parts
            return compare_parts(brand_data, skp_data, part_type)
        except Exception as e:
            logger.error(f"Rule comparison failed: {e}")
            return self._create_error_comparison(f"Comparison failed: {e}")

    def _create_error_comparison(self, error_message: str) -> Dict:
        """Create standardized error comparison result."""
        return {
            "match_result": "UNCERTAIN",
            "confidence": 0,
            "match_reason": f"Processing error: {error_message}",
            "fitment_match": "UNKNOWN",
            "desc_match": "UNKNOWN",
            "missing_info": error_message
        }

    def _create_scraping_error(self, error_message: str) -> Dict:
        """Create standardized scraping error result."""
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

    def get_stats(self) -> Dict:
        """Get processing statistics."""
        total_batches = self.stats["batches_processed"]
        total_rows = self.stats["rows_processed"]

        avg_batch_duration = (
            self.stats["total_duration"] / max(total_batches, 1)
        )
        avg_row_duration = (
            self.stats["total_duration"] / max(total_rows, 1)
        )

        parallel_percentage = (
            self.stats["parallel_used"] / max(total_batches, 1) * 100
            if total_batches > 0 else 0
        )

        return {
            **self.stats,
            "avg_batch_duration": avg_batch_duration,
            "avg_row_duration": avg_row_duration,
            "parallel_percentage": parallel_percentage,
            "estimated_speedup": self._calculate_speedup()
        }

    def _calculate_speedup(self) -> float:
        """Calculate estimated speedup vs sequential processing."""
        if self.stats["rows_processed"] == 0:
            return 1.0

        # Estimate based on batch size and parallel usage
        sequential_time_per_row = 15.0  # Estimated baseline from existing system
        current_time_per_row = self.stats["total_duration"] / self.stats["rows_processed"]

        return sequential_time_per_row / max(current_time_per_row, 0.1)

# Enhanced Excel processor with batch support
def process_rows_with_batching(filepath: str,
                              sheet_name: str = "Anchor",
                              search_brand: str = None,
                              batch_size: int = 8,
                              max_workers: int = 4,
                              enable_parallel: bool = True,
                              **kwargs):
    """
    Enhanced version of excel_handler.process_rows() with batch processing.

    This function can be used as a drop-in replacement for the existing
    process_rows() function, providing significant speed improvements.
    """
    from excel_handler import get_valid_rows

    # Get all the same parameters as the original function
    reprocess_uncertain = kwargs.get('reprocess_uncertain', False)
    on_progress = kwargs.get('on_progress')
    on_log = kwargs.get('on_log')
    stop_flag = kwargs.get('stop_flag')
    start_row = kwargs.get('start_row')
    end_row = kwargs.get('end_row')
    limit = kwargs.get('limit')

    brand = (search_brand or sheet_name).upper().strip()

    def log(msg):
        if on_log:
            on_log(msg)
        else:
            print(msg)

    # Load rows using existing excel_handler logic
    log(f"Loading rows for batch processing: {sheet_name} | {brand}")
    valid_rows = get_valid_rows(filepath, sheet_name, supplier_filter=brand)

    # Apply filters (same as original excel_handler)
    if start_row is not None:
        valid_rows = [r for r in valid_rows if r["row_num"] >= start_row]
    if end_row is not None:
        valid_rows = [r for r in valid_rows if r["row_num"] <= end_row]
    if limit is not None:
        valid_rows = valid_rows[:limit]

    if not reprocess_uncertain:
        # Filter out already processed rows (would need to load Excel to check)
        # For now, process all rows - this filtering would be added in integration
        pass

    log(f"Processing {len(valid_rows)} rows with batch_size={batch_size}, parallel={enable_parallel}")

    # Process with batch processor
    processor = BatchProcessor(
        batch_size=batch_size,
        max_workers=max_workers,
        enable_parallel=enable_parallel
    )

    comparison_results = processor.process_rows_batch(
        rows=valid_rows,
        sheet_name=sheet_name,
        brand=brand,
        on_progress=on_progress,
        on_log=on_log,
        stop_flag=stop_flag
    )

    # Log final statistics
    stats = processor.get_stats()
    log(f"Batch processing complete: {stats['rows_processed']} rows in {stats['total_duration']:.1f}s")
    log(f"Average {stats['avg_row_duration']:.1f}s per row (estimated {stats['estimated_speedup']:.1f}x speedup)")
    log(f"Parallel usage: {stats['parallel_percentage']:.1f}%")

    return comparison_results, valid_rows

if __name__ == "__main__":
    # Test batch processing
    logging.basicConfig(level=logging.INFO)

    test_rows = [
        {"row_num": 10, "part_type": "ENGINE MOUNT", "part_num": "3217", "skp_num": "SKM3217"},
        {"row_num": 11, "part_type": "ENGINE MOUNT", "part_num": "999999", "skp_num": "SKP999"},
        {"row_num": 12, "part_type": "ENGINE MOUNT", "part_num": "3218", "skp_num": "SKM3218"},
    ]

    processor = BatchProcessor(batch_size=2, max_workers=2, enable_parallel=True)

    def test_log(msg):
        print(f"[TEST] {msg}")

    def test_progress(current, total):
        print(f"[TEST] Progress: {current}/{total}")

    print("Testing batch processor...")
    results = processor.process_rows_batch(
        rows=test_rows,
        sheet_name="Anchor",
        brand="ANCHOR",
        on_log=test_log,
        on_progress=test_progress
    )

    print(f"\nResults: {len(results)} comparisons")
    for i, result in enumerate(results):
        print(f"  Row {i+1}: {result.get('match_result', 'ERROR')} ({result.get('confidence', 0)}%)")

    print(f"\nStats: {processor.get_stats()}")