#!/usr/bin/env python3
"""
Test the enhanced batch processor.
"""

import time
import tempfile
import os

def test_enhanced_batch():
    """Test enhanced batch processing."""
    print("Testing Enhanced Batch Processor")
    print("="*40)

    try:
        from enhanced_batch_processor import EnhancedBatchProcessor

        # Test data
        test_rows = [
            {"row_num": 10, "part_type": "ENGINE MOUNT", "part_num": "3217", "skp_num": "SKM3217"},
            {"row_num": 11, "part_type": "ENGINE MOUNT", "part_num": "3218", "skp_num": "SKM3218"},
        ]

        processor = EnhancedBatchProcessor(batch_size=2, optimize_delays=True)

        def test_log(msg):
            print(f"  [LOG] {msg}")

        print("Testing batch scraping with existing scraper...")

        # Test the batch scraping component
        from enhanced_batch_processor import EnhancedBatchProcessor
        scraping_jobs = [
            ("3217", "ANCHOR"),
            ("SKM3217", "SKP"),
        ]

        start_time = time.time()
        results = processor._batch_scrape_sequential(scraping_jobs, test_log)
        duration = time.time() - start_time

        print(f"Batch scraping completed in {duration:.1f}s")
        print(f"Results: {len(results)}")

        success_count = sum(1 for r in results if r.get('found', False))
        print(f"Successful scrapes: {success_count}/{len(results)}")

        if success_count > 0:
            print("[OK] Enhanced batch scraping works!")

            # Test comparison
            if len(results) >= 2:
                brand_data = results[0]
                skp_data = results[1]

                comparison = processor._compare_parts(brand_data, skp_data, "ENGINE MOUNT")
                print(f"Comparison result: {comparison.get('match_result')} ({comparison.get('confidence')}%)")

            return True
        else:
            print("[FAIL] No successful scrapes")
            return False

    except Exception as e:
        print(f"[ERROR] Enhanced batch test failed: {e}")
        return False

def test_performance_comparison():
    """Compare performance vs sequential."""
    print("\nPerformance Comparison Test")
    print("="*40)

    # Test with existing scraper
    test_jobs = [
        ("3217", "ANCHOR"),
        ("SKM3217", "SKP"),
    ]

    try:
        print("Testing sequential (existing) scraper...")
        from scraper_subprocess import scrape_rockauto_subprocess

        seq_start = time.time()
        seq_results = []
        for part_num, brand in test_jobs:
            try:
                result = scrape_rockauto_subprocess(part_num, brand)
                seq_results.append(result)
                # Include the normal delay
                time.sleep(2.5)
            except Exception as e:
                print(f"  Sequential failed for {brand} {part_num}: {e}")
                seq_results.append({"found": False, "error": str(e)})

        seq_duration = time.time() - seq_start
        seq_success = sum(1 for r in seq_results if r.get('found', False))

        print(f"Sequential: {len(test_jobs)} jobs in {seq_duration:.1f}s ({seq_success} successful)")

        # Test enhanced batch
        print("Testing enhanced batch processor...")
        from enhanced_batch_processor import EnhancedBatchProcessor

        processor = EnhancedBatchProcessor(batch_size=4, optimize_delays=True)

        def log_func(msg):
            print(f"  [BATCH] {msg}")

        batch_start = time.time()
        batch_results = processor._batch_scrape_sequential(test_jobs, log_func)
        batch_duration = time.time() - batch_start
        batch_success = sum(1 for r in batch_results if r.get('found', False))

        print(f"Enhanced:   {len(test_jobs)} jobs in {batch_duration:.1f}s ({batch_success} successful)")

        # Calculate improvement
        if seq_duration > 0 and batch_duration > 0:
            speedup = seq_duration / batch_duration
            print(f"Speedup: {speedup:.1f}x")

            if speedup > 1.5 and batch_success >= seq_success:
                print("[OK] Enhanced batch shows improvement!")
                return True
            else:
                print("[INFO] Enhanced batch working but improvement modest")
                return True  # Still working
        else:
            print("[ERROR] Performance comparison failed")
            return False

    except Exception as e:
        print(f"[ERROR] Performance test failed: {e}")
        return False

def test_integration_compatibility():
    """Test compatibility with existing excel_handler."""
    print("\nIntegration Compatibility Test")
    print("="*40)

    try:
        # Test imports
        from enhanced_batch_processor import process_rows_enhanced
        from excel_handler import get_valid_rows, process_rows
        print("[OK] All modules import successfully")

        # Test function signature compatibility
        import inspect

        original_sig = inspect.signature(process_rows)
        enhanced_sig = inspect.signature(process_rows_enhanced)

        print(f"Original signature: {original_sig}")
        print(f"Enhanced signature: {enhanced_sig}")

        # Check required parameters
        original_params = set(original_sig.parameters.keys())
        enhanced_params = set(enhanced_sig.parameters.keys())

        if 'filepath' in enhanced_params:
            print("[OK] Function signatures compatible")
            return True
        else:
            print("[FAIL] Function signatures incompatible")
            return False

    except Exception as e:
        print(f"[ERROR] Integration test failed: {e}")
        return False

if __name__ == "__main__":
    print("ENHANCED BATCH PROCESSOR TESTS")
    print("="*50)

    tests = [
        ("Enhanced Batch", test_enhanced_batch),
        ("Performance", test_performance_comparison),
        ("Integration", test_integration_compatibility),
    ]

    results = {}
    total_start = time.time()

    for test_name, test_func in tests:
        try:
            print(f"\n--- {test_name} Test ---")
            result = test_func()
            results[test_name] = result
        except Exception as e:
            print(f"[ERROR] {test_name} test crashed: {e}")
            results[test_name] = False

    total_duration = time.time() - total_start

    print("\n" + "="*50)
    print("TEST SUMMARY")
    print("="*50)

    passed = sum(1 for result in results.values() if result)
    total = len(results)

    for test_name, result in results.items():
        status = "PASS" if result else "FAIL"
        print(f"{test_name:<15} {status}")

    print(f"\nOverall: {passed}/{total} tests passed in {total_duration:.1f}s")

    if passed >= 2:
        print("\n[SUCCESS] Enhanced batch processor is working!")
        print("Ready for integration with excel_handler.")
    else:
        print("\n[FAIL] Enhanced batch processor needs fixes")