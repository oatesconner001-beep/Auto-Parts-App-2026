"""
PHASE 2: Parallel Image Processor — Process cached image URLs with multiple Ollama instances.

Speed optimization:
- Load cached image URLs from Phase 1
- Download images concurrently
- Run multiple Ollama moondream instances in parallel
- No browser scraping needed (already done in Phase 1)
"""

import sys
import json
import time
import asyncio
import aiohttp
import concurrent.futures
from pathlib import Path
from datetime import datetime
import base64

# Import existing vision processors
_src = Path(__file__).parent
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from local_vision import compare_images, check_ollama
from image_compare import compare_part_images

CACHE_DIR = Path(__file__).parent.parent / "image_cache"
RESULTS_DIR = Path(__file__).parent.parent / "comparison_results"
RESULTS_DIR.mkdir(exist_ok=True)

async def download_image(session, url):
    """Download image and return base64 encoded data"""
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
            if response.status == 200:
                data = await response.read()
                return base64.b64encode(data).decode()
            return None
    except Exception as e:
        print(f"Download error for {url}: {e}")
        return None

async def download_image_pair(session, brand_url, skp_url):
    """Download both images concurrently"""
    tasks = []
    if brand_url:
        tasks.append(download_image(session, brand_url))
    if skp_url:
        tasks.append(download_image(session, skp_url))

    results = await asyncio.gather(*tasks, return_exceptions=True)

    brand_data = None
    skp_data = None

    if brand_url and len(results) > 0 and not isinstance(results[0], Exception):
        brand_data = results[0]

    if skp_url:
        idx = 1 if brand_url else 0
        if len(results) > idx and not isinstance(results[idx], Exception):
            skp_data = results[idx]

    return brand_data, skp_data

def process_image_pair_sync(part_key, part_data, brand_data, skp_data):
    """Process a single image pair using local vision (synchronous)"""
    result = {
        'part_key': part_key,
        'part_num': part_data['part_num'],
        'skp_num': part_data['skp_num'],
        'row_num': part_data['row_num'],
        'processed_at': datetime.now().isoformat(),
        'cv_score': 0.0,
        'cv_details': {},
        'ai_result': None,
        'ai_confidence': 0,
        'final_verdict': 'UNCERTAIN',
        'upgrade_to_likely': False,
        'error': None
    }

    try:
        if not brand_data or not skp_data:
            result['error'] = 'Missing image data'
            return result

        # Phase 1: Local CV comparison (fast)
        print(f"  CV comparing: {part_data['part_num']} vs {part_data['skp_num']}")
        cv_result = compare_part_images(brand_data, skp_data)

        if cv_result and isinstance(cv_result, dict):
            result['cv_score'] = cv_result.get('overall_score', 0.0)
            result['cv_details'] = cv_result

            # High CV similarity = instant upgrade
            if result['cv_score'] >= 0.75:
                result['final_verdict'] = 'LIKELY'
                result['upgrade_to_likely'] = True
                result['ai_result'] = 'HIGH_CV'
                result['ai_confidence'] = int(result['cv_score'] * 100)
                print(f"    [OK] HIGH CV ({result['cv_score']:.3f}) -> LIKELY")
                return result

        # Phase 2: AI vision comparison (for medium CV scores)
        if result['cv_score'] >= 0.35:  # MEDIUM range
            print(f"    🤖 AI comparing (CV: {result['cv_score']:.3f})...")

            # Use local Ollama moondream
            ai_result = compare_images(brand_data, skp_data)

            if ai_result and isinstance(ai_result, dict):
                result['ai_result'] = ai_result.get('result', 'UNCERTAIN')
                result['ai_confidence'] = ai_result.get('confidence', 0)

                # Check if AI suggests upgrade
                if (result['ai_result'] in ['YES', 'LIKELY'] and
                    result['ai_confidence'] >= 65):
                    result['final_verdict'] = 'LIKELY'
                    result['upgrade_to_likely'] = True
                    print(f"    [OK] AI {result['ai_result']} ({result['ai_confidence']}%) -> LIKELY")
                else:
                    print(f"    ℹ️ AI {result['ai_result']} ({result['ai_confidence']}%) -> keep UNCERTAIN")
            else:
                print(f"    ⚠️ AI comparison failed")
        else:
            print(f"    ⏭️ Low CV ({result['cv_score']:.3f}) -> skip AI")

    except Exception as e:
        result['error'] = str(e)
        print(f"    [FAIL] Processing error: {e}")

    return result

async def process_batch_parallel(image_pairs, max_workers=4):
    """Process image pairs with parallel AI processing"""

    # Download all images concurrently
    print(f"📥 Downloading {len(image_pairs)} image pairs...")

    async with aiohttp.ClientSession() as session:
        download_tasks = []

        for part_key, part_data in image_pairs.items():
            if part_data['found_images'] >= 2:  # Both images available
                download_tasks.append(download_image_pair(
                    session,
                    part_data.get('brand_image_url'),
                    part_data.get('skp_image_url')
                ))
            else:
                download_tasks.append(asyncio.create_task(asyncio.sleep(0)))  # Placeholder

        download_results = await asyncio.gather(*download_tasks, return_exceptions=True)

    # Process comparisons with ThreadPoolExecutor for CPU-bound AI work
    print(f"🤖 Processing {len(image_pairs)} comparisons with {max_workers} workers...")

    results = []
    processed = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_part = {}

        idx = 0
        for part_key, part_data in image_pairs.items():
            if part_data['found_images'] >= 2 and idx < len(download_results):
                download_result = download_results[idx]
                if isinstance(download_result, tuple) and len(download_result) == 2:
                    brand_data, skp_data = download_result
                    if brand_data and skp_data:
                        future = executor.submit(
                            process_image_pair_sync,
                            part_key, part_data, brand_data, skp_data
                        )
                        future_to_part[future] = part_key
            idx += 1

        # Collect results as they complete
        for future in concurrent.futures.as_completed(future_to_part):
            result = future.result()
            results.append(result)
            processed += 1

            if processed % 10 == 0 or processed == len(future_to_part):
                upgrades = sum(1 for r in results if r.get('upgrade_to_likely', False))
                print(f"    Progress: {processed}/{len(future_to_part)} | Upgrades: {upgrades}")

    return results

def parallel_process_images(sheet_name, max_workers=4, limit=None):
    """Phase 2: Process cached images with parallel AI comparison"""

    # Check Ollama availability
    if not check_ollama():
        print("[FAIL] Ollama not available. Please start Ollama service.")
        return None, 0, 0

    cache_file = CACHE_DIR / f"{sheet_name.lower()}_image_urls.json"
    results_file = RESULTS_DIR / f"{sheet_name.lower()}_comparisons.json"

    if not cache_file.exists():
        print(f"[FAIL] Cache file not found: {cache_file}")
        print("   Run Phase 1 (bulk_image_scraper.py) first!")
        return None, 0, 0

    # Load cached image URLs
    print(f"Loading cached URLs: {cache_file}")
    with open(cache_file, 'r') as f:
        cached_data = json.load(f)

    # Filter pairs with both images
    image_pairs = {k: v for k, v in cached_data.items() if v.get('found_images', 0) >= 2}

    if limit:
        image_pairs = dict(list(image_pairs.items())[:limit])

    print(f"\n🖼️ PARALLEL PROCESSING: {len(image_pairs)} image pairs")
    print(f"Workers: {max_workers} | Results: {results_file}")

    if len(image_pairs) == 0:
        print("[FAIL] No image pairs available for processing")
        return results_file, 0, 0

    # Process in parallel
    start_time = time.time()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        results = loop.run_until_complete(process_batch_parallel(image_pairs, max_workers))
    finally:
        loop.close()

    # Save results
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2)

    elapsed = time.time() - start_time
    upgrades = sum(1 for r in results if r.get('upgrade_to_likely', False))

    print(f"\n[OK] PARALLEL PROCESSING COMPLETE")
    print(f"   Processed: {len(results):,} pairs")
    print(f"   Upgrades: {upgrades:,} ({upgrades/len(results)*100:.1f}%)")
    print(f"   Time: {elapsed:.1f}s ({len(results)/elapsed:.1f} pairs/s)")
    print(f"   Results: {results_file}")

    return results_file, len(results), upgrades

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("sheet", choices=["Anchor", "Dorman", "GMB", "SMP", "Four Seasons"], help="Sheet to process")
    parser.add_argument("--workers", type=int, default=4, help="Number of parallel workers")
    parser.add_argument("--limit", type=int, help="Limit number of pairs")

    args = parser.parse_args()

    parallel_process_images(args.sheet, args.workers, args.limit)