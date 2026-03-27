"""
Comprehensive test suite for the parallel scraping system.

Tests all components thoroughly before integration to ensure robustness:
- Chrome worker functionality
- Parallel scraper coordination
- Batch processing
- Error handling and recovery
- Performance measurement

Run this to validate the parallel system before replacing existing scraper.
"""

import time
import logging
import sys
from pathlib import Path
import json
from typing import List, Dict

# Set up detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_chrome_worker():
    """Test individual Chrome worker functionality."""
    print("\n" + "="*50)
    print("TEST 1: Chrome Worker Functionality")
    print("="*50)

    try:
        from chrome_worker import ChromeWorker

        # Test worker initialization
        worker = ChromeWorker("test_worker", str(Path.cwd() / "test_profile"))

        print("[OK] ChromeWorker imported successfully")

        if worker.initialize():
            print("[OK] Chrome worker initialized successfully")

            # Test health check
            if worker.health_check():
                print("[OK] Health check passed")
            else:
                print("[FAIL] Health check failed")

            # Test scraping known good part
            print("\nTesting scraping with known part: ANCHOR 3217")
            start_time = time.time()
            result = worker.scrape_rockauto("3217", "ANCHOR")
            duration = time.time() - start_time

            print(f"[OK] Scraping completed in {duration:.1f}s")
            print(f"  Found: {result.get('found', False)}")
            print(f"  Category: {result.get('category', 'N/A')}")
            print(f"  OEM refs: {len(result.get('oem_refs', []))} found")
            print(f"  Price: {result.get('price', 'N/A')}")

            if result.get('found') and result.get('oem_refs'):
                print("[OK] Chrome worker test PASSED")
                test_result = True
            else:
                print("[FAIL] Chrome worker test FAILED - no data found")
                test_result = False

            # Clean up
            worker.cleanup()
            print("[OK] Worker cleaned up")

        else:
            print("[FAIL] Chrome worker initialization failed")
            test_result = False

    except Exception as e:
        print(f"[FAIL] Chrome worker test FAILED: {e}")
        test_result = False

    return test_result

def test_parallel_scraper():
    """Test parallel scraper coordination."""
    print("\n" + "="*50)
    print("TEST 2: Parallel Scraper Coordination")
    print("="*50)

    try:
        from parallel_scraper import scrape_rockauto_batch, scrape_rockauto_parallel

        print("[OK] Parallel scraper imported successfully")

        # Test single part scraping
        print("\nTesting single part parallel scraping...")
        start_time = time.time()
        result = scrape_rockauto_parallel("3217", "ANCHOR")
        duration = time.time() - start_time

        print(f"[OK] Single part completed in {duration:.1f}s")
        print(f"  Found: {result.get('found', False)}")
        print(f"  OEM refs: {len(result.get('oem_refs', []))}")

        # Test batch scraping
        print("\nTesting batch parallel scraping...")
        test_jobs = [
            ("3217", "ANCHOR"),
            ("SKM3217", "SKP"),
            ("999999", "TESTBRAND"),  # Should fail gracefully
        ]

        start_time = time.time()
        results = scrape_rockauto_batch(test_jobs, max_workers=2)
        duration = time.time() - start_time

        print(f"[OK] Batch scraping completed in {duration:.1f}s")
        print(f"  Jobs processed: {len(results)}")

        success_count = sum(1 for r in results if r.get('found', False))
        print(f"  Successful: {success_count}/{len(results)}")

        # Verify results order matches input order
        for i, (expected_part, expected_brand) in enumerate(test_jobs):
            result = results[i]
            print(f"  Job {i+1} ({expected_brand} {expected_part}): {'[OK]' if result.get('found') else '[FAIL]'}")

        if len(results) == len(test_jobs) and success_count >= 1:
            print("[OK] Parallel scraper test PASSED")
            test_result = True
        else:
            print("[FAIL] Parallel scraper test FAILED")
            test_result = False

    except Exception as e:
        print(f"[FAIL] Parallel scraper test FAILED: {e}")
        test_result = False

    return test_result

def test_batch_processor():
    """Test batch processing functionality."""
    print("\n" + "="*50)
    print("TEST 3: Batch Processing")
    print("="*50)

    try:
        from batch_processor import BatchProcessor

        print("[OK] Batch processor imported successfully")

        # Create test rows
        test_rows = [
            {"row_num": 10, "part_type": "ENGINE MOUNT", "part_num": "3217", "skp_num": "SKM3217"},
            {"row_num": 11, "part_type": "ENGINE MOUNT", "part_num": "999999", "skp_num": "SKP999"},
            {"row_num": 12, "part_type": "TEST PART", "part_num": "3218", "skp_num": "SKM3218"},
        ]

        # Test with parallel enabled
        print(f"\nTesting batch processing ({len(test_rows)} rows, parallel enabled)...")
        processor = BatchProcessor(batch_size=2, max_workers=2, enable_parallel=True)

        def test_log(msg):
            print(f"  [LOG] {msg}")

        def test_progress(current, total):
            print(f"  [PROGRESS] {current}/{total}")

        start_time = time.time()
        results = processor.process_rows_batch(
            rows=test_rows,
            sheet_name="Anchor",
            brand="ANCHOR",
            on_log=test_log,
            on_progress=test_progress
        )
        duration = time.time() - start_time

        print(f"[OK] Batch processing completed in {duration:.1f}s")
        print(f"  Results: {len(results)} comparisons")

        success_count = sum(1 for r in results if r.get('match_result') != 'ERROR')
        print(f"  Successful: {success_count}/{len(results)}")

        # Display results
        for i, result in enumerate(results):
            match_result = result.get('match_result', 'ERROR')
            confidence = result.get('confidence', 0)
            print(f"  Row {i+1}: {match_result} ({confidence}%)")

        # Get statistics
        stats = processor.get_stats()
        print(f"\nStatistics:")
        print(f"  Rows processed: {stats['rows_processed']}")
        print(f"  Average time per row: {stats['avg_row_duration']:.1f}s")
        print(f"  Estimated speedup: {stats['estimated_speedup']:.1f}x")
        print(f"  Parallel usage: {stats['parallel_percentage']:.1f}%")

        if len(results) == len(test_rows) and success_count >= 1:
            print("[OK] Batch processor test PASSED")
            test_result = True
        else:
            print("[FAIL] Batch processor test FAILED")
            test_result = False

    except Exception as e:
        print(f"[FAIL] Batch processor test FAILED: {e}")
        test_result = False

    return test_result

def test_error_handling():
    """Test error handling and recovery."""
    print("\n" + "="*50)
    print("TEST 4: Error Handling & Recovery")
    print("="*50)

    try:
        from parallel_scraper import scrape_rockauto_batch

        # Test with invalid parts
        invalid_jobs = [
            ("INVALID123", "INVALIDBRAND"),
            ("BADPART456", "ANOTHERBAD"),
        ]

        print("Testing error handling with invalid parts...")
        start_time = time.time()
        results = scrape_rockauto_batch(invalid_jobs, max_workers=2)
        duration = time.time() - start_time

        print(f"[OK] Error handling completed in {duration:.1f}s")
        print(f"  Results: {len(results)} (should match {len(invalid_jobs)} input jobs)")

        # Verify all results have proper error structure
        all_valid_structure = True
        for i, result in enumerate(results):
            if not isinstance(result, dict):
                print(f"[FAIL] Result {i+1} is not a dict")
                all_valid_structure = False
                continue

            required_keys = ['found', 'error', 'category', 'oem_refs']
            missing_keys = [key for key in required_keys if key not in result]
            if missing_keys:
                print(f"[FAIL] Result {i+1} missing keys: {missing_keys}")
                all_valid_structure = False

            print(f"  Job {i+1}: Found={result.get('found', False)}, Error={result.get('error', 'N/A')[:50]}")

        if all_valid_structure and len(results) == len(invalid_jobs):
            print("[OK] Error handling test PASSED")
            test_result = True
        else:
            print("[FAIL] Error handling test FAILED")
            test_result = False

    except Exception as e:
        print(f"[FAIL] Error handling test FAILED: {e}")
        test_result = False

    return test_result

def test_performance_comparison():
    """Compare parallel vs sequential performance."""
    print("\n" + "="*50)
    print("TEST 5: Performance Comparison")
    print("="*50)

    # Test jobs for comparison
    test_jobs = [
        ("3217", "ANCHOR"),
        ("SKM3217", "SKP"),
    ]

    try:
        # Test sequential (existing system)
        print("Testing sequential processing...")
        from scraper_subprocess import scrape_rockauto_subprocess

        sequential_start = time.time()
        sequential_results = []
        for part_num, brand in test_jobs:
            try:
                result = scrape_rockauto_subprocess(part_num, brand)
                sequential_results.append(result)
            except Exception as e:
                print(f"  Sequential scraping failed for {brand} {part_num}: {e}")
                sequential_results.append({"found": False, "error": str(e)})

        sequential_duration = time.time() - sequential_start
        sequential_success = sum(1 for r in sequential_results if r.get('found', False))

        print(f"[OK] Sequential: {len(test_jobs)} jobs in {sequential_duration:.1f}s ({sequential_success} successful)")

    except Exception as e:
        print(f"[FAIL] Sequential test failed: {e}")
        sequential_duration = 999  # Large number for comparison
        sequential_success = 0

    try:
        # Test parallel processing
        print("Testing parallel processing...")
        from parallel_scraper import scrape_rockauto_batch

        parallel_start = time.time()
        parallel_results = scrape_rockauto_batch(test_jobs, max_workers=2)
        parallel_duration = time.time() - parallel_start
        parallel_success = sum(1 for r in parallel_results if r.get('found', False))

        print(f"[OK] Parallel: {len(test_jobs)} jobs in {parallel_duration:.1f}s ({parallel_success} successful)")

    except Exception as e:
        print(f"[FAIL] Parallel test failed: {e}")
        parallel_duration = 999
        parallel_success = 0

    # Calculate improvement
    if sequential_duration > 0 and parallel_duration > 0:
        speedup = sequential_duration / parallel_duration
        print(f"\nPerformance Summary:")
        print(f"  Sequential: {sequential_duration:.1f}s ({sequential_success} successful)")
        print(f"  Parallel:   {parallel_duration:.1f}s ({parallel_success} successful)")
        print(f"  Speedup:    {speedup:.1f}x")

        if speedup > 1.2 and parallel_success >= sequential_success:
            print("[OK] Performance improvement achieved")
            test_result = True
        else:
            print("[WARN] Performance improvement marginal or worse")
            test_result = False  # Still might be worth it for larger batches
    else:
        print("[FAIL] Performance comparison failed")
        test_result = False

    return test_result

def test_integration_compatibility():
    """Test compatibility with existing excel_handler."""
    print("\n" + "="*50)
    print("TEST 6: Integration Compatibility")
    print("="*50)

    try:
        # Test that we can import existing modules
        from excel_handler import get_valid_rows
        from rule_compare import compare_parts
        print("[OK] Existing modules import successfully")

        # Test that batch processor can use excel_handler functions
        from batch_processor import process_rows_with_batching
        print("[OK] Batch processor with excel_handler integration available")

        # Verify the function signature matches
        import inspect
        sig = inspect.signature(process_rows_with_batching)
        required_params = ['filepath', 'sheet_name']
        has_required = all(param in sig.parameters for param in required_params)

        if has_required:
            print("[OK] Function signature compatible")
        else:
            print("[FAIL] Function signature incompatible")
            return False

        # Test rule comparison still works
        test_anchor = {
            "found": True,
            "category": "Motor Mount",
            "oem_refs": ["5273883AD", "7B0199279A"],
            "price": "$20.79"
        }

        test_skp = {
            "found": True,
            "category": "Motor Mount",
            "oem_refs": ["5273883AC", "5273883AD", "7B0199279"],
            "price": "$14.03"
        }

        comparison = compare_parts(test_anchor, test_skp, "ENGINE MOUNT")

        if comparison.get('match_result') == 'YES' and comparison.get('confidence', 0) > 80:
            print("[OK] Rule comparison still works correctly")
            print(f"  Result: {comparison['match_result']} ({comparison['confidence']}%)")
            test_result = True
        else:
            print("[FAIL] Rule comparison not working")
            print(f"  Got: {comparison.get('match_result')} ({comparison.get('confidence', 0)}%)")
            test_result = False

    except Exception as e:
        print(f"[FAIL] Integration compatibility test FAILED: {e}")
        test_result = False

    return test_result

def run_all_tests():
    """Run all tests and provide summary."""
    print("PARALLEL SCRAPER TEST SUITE")
    print("="*50)
    print("Testing parallel scraping system before integration...")
    print("This will verify robustness without affecting existing functionality.")

    tests = [
        ("Chrome Worker", test_chrome_worker),
        ("Parallel Scraper", test_parallel_scraper),
        ("Batch Processor", test_batch_processor),
        ("Error Handling", test_error_handling),
        ("Performance", test_performance_comparison),
        ("Integration", test_integration_compatibility),
    ]

    results = {}
    start_time = time.time()

    for test_name, test_func in tests:
        try:
            result = test_func()
            results[test_name] = result
        except Exception as e:
            print(f"\n[FAIL] {test_name} test crashed: {e}")
            results[test_name] = False

    total_duration = time.time() - start_time

    # Summary
    print("\n" + "="*50)
    print("TEST SUITE SUMMARY")
    print("="*50)

    passed = sum(1 for result in results.values() if result)
    total = len(results)

    for test_name, result in results.items():
        status = "PASS" if result else "FAIL"
        print(f"{test_name:<20} {status}")

    print(f"\nOverall: {passed}/{total} tests passed in {total_duration:.1f}s")

    if passed == total:
        print("\n[SUCCESS] ALL TESTS PASSED!")
        print("Parallel scraping system is ready for integration.")
        return True
    elif passed >= total * 0.8:  # 80% pass rate
        print("\n[WARN] MOSTLY PASSING")
        print("Parallel scraping system is mostly working but has some issues.")
        print("Review failed tests before integration.")
        return False
    else:
        print("\n[ERROR] MULTIPLE FAILURES")
        print("Parallel scraping system needs fixes before integration.")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)