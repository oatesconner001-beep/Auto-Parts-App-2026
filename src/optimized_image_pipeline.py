"""
OPTIMIZED IMAGE ANALYSIS PIPELINE

Master script that runs all three phases for maximum speed:

Phase 1: Bulk Image URL Scraping (headless, no browser interference)
Phase 2: Parallel Image Processing (4+ workers, concurrent AI)
Phase 3: Batch Excel Updates (single save operation)

Expected speed improvement: 5-10x faster than original approach
"""

import sys
import time
import argparse
from pathlib import Path

_src = Path(__file__).parent
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from bulk_image_scraper import bulk_scrape_images
from parallel_image_processor import parallel_process_images
from batch_excel_updater import batch_update_excel

def run_optimized_pipeline(sheet_name, max_workers=4, limit=None, dry_run=False):
    """Run the complete optimized image analysis pipeline"""

    print(">> OPTIMIZED IMAGE ANALYSIS PIPELINE")
    print("=" * 60)
    print(f"Sheet: {sheet_name}")
    print(f"Workers: {max_workers}")
    print(f"Limit: {limit or 'None'}")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    print()

    total_start = time.time()

    # PHASE 1: Bulk Image URL Scraping
    print("-- PHASE 1: BULK IMAGE SCRAPING")
    print("-" * 40)

    phase1_start = time.time()
    try:
        cache_file, processed, found_images = bulk_scrape_images(sheet_name, limit)
        phase1_time = time.time() - phase1_start

        print(f"[OK] Phase 1 complete in {phase1_time:.1f}s")
        print(f"   Processed: {processed:,} rows")
        print(f"   Found images: {found_images:,}")
        print()

        if found_images == 0:
            print("[FAIL] No images found - cannot proceed to Phase 2")
            return False

    except Exception as e:
        print(f"[FAIL] Phase 1 failed: {e}")
        return False

    # PHASE 2: Parallel Image Processing
    print("🖼️ PHASE 2: PARALLEL PROCESSING")
    print("-" * 40)

    phase2_start = time.time()
    try:
        results_file, comparisons, upgrades = parallel_process_images(
            sheet_name, max_workers, limit
        )
        phase2_time = time.time() - phase2_start

        print(f"[OK] Phase 2 complete in {phase2_time:.1f}s")
        print(f"   Comparisons: {comparisons:,}")
        print(f"   Upgrades: {upgrades:,}")
        print()

        if not results_file:
            print("[FAIL] Phase 2 failed - no results file")
            return False

    except Exception as e:
        print(f"[FAIL] Phase 2 failed: {e}")
        return False

    # PHASE 3: Batch Excel Updates
    print("📝 PHASE 3: BATCH EXCEL UPDATE")
    print("-" * 40)

    phase3_start = time.time()
    try:
        success = batch_update_excel(sheet_name, dry_run)
        phase3_time = time.time() - phase3_start

        if success:
            print(f"[OK] Phase 3 complete in {phase3_time:.1f}s")
        else:
            print(f"[FAIL] Phase 3 failed")
            return False

    except Exception as e:
        print(f"[FAIL] Phase 3 failed: {e}")
        return False

    # SUMMARY
    total_time = time.time() - total_start

    print()
    print("🏆 OPTIMIZATION COMPLETE!")
    print("=" * 60)
    print(f"Total time: {total_time:.1f}s")
    print(f"Phase 1 (Scraping): {phase1_time:.1f}s ({phase1_time/total_time*100:.1f}%)")
    print(f"Phase 2 (Processing): {phase2_time:.1f}s ({phase2_time/total_time*100:.1f}%)")
    print(f"Phase 3 (Excel): {phase3_time:.1f}s ({phase3_time/total_time*100:.1f}%)")
    print()
    print(f"📊 Performance:")
    print(f"   Rows processed: {processed:,}")
    print(f"   Images found: {found_images:,}")
    print(f"   Comparisons: {comparisons:,}")
    print(f"   Upgrades: {upgrades:,}")
    print(f"   Overall rate: {processed/total_time:.1f} rows/s")

    if not dry_run:
        print(f"   Success rate: {upgrades/comparisons*100:.1f}% of comparisons upgraded")

    return True

def estimate_performance(sheet_name):
    """Estimate performance improvement for the full dataset"""

    # Get current uncertain count
    from bulk_image_scraper import collect_uncertain_rows
    uncertain_rows = collect_uncertain_rows(sheet_name)
    total_uncertain = len(uncertain_rows)

    print(f"📊 PERFORMANCE ESTIMATION - {sheet_name}")
    print("=" * 50)
    print(f"Total UNCERTAIN rows: {total_uncertain:,}")
    print()

    # Current system estimates
    current_time_per_row = 14  # seconds (based on previous testing)
    current_total_time = total_uncertain * current_time_per_row / 3600  # hours

    # Optimized system estimates
    optimized_time_per_row = 1.5  # seconds (based on parallel processing)
    optimized_total_time = total_uncertain * optimized_time_per_row / 3600  # hours

    speedup = current_total_time / optimized_total_time if optimized_total_time > 0 else 0

    print(f"CURRENT SYSTEM:")
    print(f"  Time per row: ~{current_time_per_row}s")
    print(f"  Total time: ~{current_total_time:.1f} hours")
    print()
    print(f"OPTIMIZED SYSTEM:")
    print(f"  Time per row: ~{optimized_time_per_row}s")
    print(f"  Total time: ~{optimized_total_time:.1f} hours")
    print()
    print(f"SPEED: SPEED IMPROVEMENT: {speedup:.1f}x faster")
    print(f"⏰ TIME SAVED: {current_total_time - optimized_total_time:.1f} hours")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Optimized Image Analysis Pipeline")
    parser.add_argument("sheet", choices=["Anchor", "Dorman", "GMB", "SMP", "Four Seasons"],
                       help="Sheet to process")
    parser.add_argument("--workers", type=int, default=4,
                       help="Number of parallel workers (default: 4)")
    parser.add_argument("--limit", type=int,
                       help="Limit number of rows for testing")
    parser.add_argument("--dry-run", action="store_true",
                       help="Preview changes without applying to Excel")
    parser.add_argument("--estimate", action="store_true",
                       help="Show performance estimates and exit")

    args = parser.parse_args()

    if args.estimate:
        estimate_performance(args.sheet)
    else:
        success = run_optimized_pipeline(
            args.sheet,
            args.workers,
            args.limit,
            args.dry_run
        )

        if not success:
            sys.exit(1)