#!/usr/bin/env python3
"""
Simple scraping test to verify the parallel scraper works.
"""

import time

def test_single_scrape():
    """Test single part scraping."""
    print("Testing single part scraping...")

    try:
        from parallel_scraper import scrape_rockauto_parallel

        start_time = time.time()
        result = scrape_rockauto_parallel("3217", "ANCHOR")
        duration = time.time() - start_time

        print(f"Single scrape completed in {duration:.1f}s")
        print(f"Found: {result.get('found', False)}")
        print(f"Category: {result.get('category', 'N/A')}")
        print(f"OEM refs: {len(result.get('oem_refs', []))}")
        print(f"Error: {result.get('error', 'None')}")

        return result.get('found', False)

    except Exception as e:
        print(f"Single scrape failed: {e}")
        return False

def test_batch_scrape():
    """Test batch scraping."""
    print("\nTesting batch scraping...")

    try:
        from parallel_scraper import scrape_rockauto_batch

        jobs = [
            ("3217", "ANCHOR"),
            ("SKM3217", "SKP"),
        ]

        start_time = time.time()
        results = scrape_rockauto_batch(jobs, max_workers=2)
        duration = time.time() - start_time

        print(f"Batch scrape completed in {duration:.1f}s")
        print(f"Jobs: {len(results)}")

        success_count = 0
        for i, result in enumerate(results):
            found = result.get('found', False)
            if found:
                success_count += 1
            print(f"  Job {i+1}: Found={found}, OEMs={len(result.get('oem_refs', []))}")

        print(f"Success rate: {success_count}/{len(results)}")
        return success_count > 0

    except Exception as e:
        print(f"Batch scrape failed: {e}")
        return False

def test_fallback():
    """Test fallback to sequential processing."""
    print("\nTesting fallback to sequential...")

    try:
        from batch_processor import BatchProcessor

        # Test with small batch and parallel disabled
        processor = BatchProcessor(batch_size=2, enable_parallel=False)

        test_rows = [
            {"row_num": 1, "part_type": "ENGINE MOUNT", "part_num": "3217", "skp_num": "SKM3217"}
        ]

        start_time = time.time()
        results = processor.process_rows_batch(test_rows, "Test", "ANCHOR")
        duration = time.time() - start_time

        print(f"Fallback test completed in {duration:.1f}s")
        print(f"Results: {len(results)}")

        if results:
            result = results[0]
            print(f"Match result: {result.get('match_result', 'ERROR')}")
            print(f"Confidence: {result.get('confidence', 0)}%")

        return len(results) > 0

    except Exception as e:
        print(f"Fallback test failed: {e}")
        return False

if __name__ == "__main__":
    print("SIMPLIFIED PARALLEL SCRAPER TESTS")
    print("="*50)

    tests = [
        ("Single Scrape", test_single_scrape),
        ("Batch Scrape", test_batch_scrape),
        ("Fallback", test_fallback),
    ]

    results = {}
    for test_name, test_func in tests:
        try:
            result = test_func()
            results[test_name] = result
        except Exception as e:
            print(f"{test_name} crashed: {e}")
            results[test_name] = False

    print("\n" + "="*50)
    print("TEST SUMMARY")
    print("="*50)

    passed = sum(1 for result in results.values() if result)
    total = len(results)

    for test_name, result in results.items():
        status = "PASS" if result else "FAIL"
        print(f"{test_name:<15} {status}")

    print(f"\nOverall: {passed}/{total} tests passed")

    if passed >= 2:
        print("\n[SUCCESS] Parallel scraper is working!")
    else:
        print("\n[FAIL] Parallel scraper needs fixes")