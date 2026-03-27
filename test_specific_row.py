#!/usr/bin/env python3
"""Test image analysis on a specific UNCERTAIN row."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

print("Testing specific row image analysis...")

# Test ANCHOR 3503 vs SKP SKM3503 (Row 151)
from scraper_subprocess import scrape_rockauto_subprocess as scrape_rockauto
from local_vision import compare_images
# from image_compare import compare_images_cv

print("1. Testing ANCHOR 3503 scraping...")
anchor_result = scrape_rockauto("3503", "ANCHOR")
print(f"ANCHOR found: {anchor_result.get('found')}")
print(f"ANCHOR image: {anchor_result.get('image_url')}")

print("\n2. Testing SKP SKM3503 scraping...")
skp_result = scrape_rockauto("SKM3503", "SKP")
print(f"SKP found: {skp_result.get('found')}")
print(f"SKP image: {skp_result.get('image_url')}")

if anchor_result.get('image_url') and skp_result.get('image_url'):
    print("\n3. Testing image comparison...")
    try:
        vision_result = compare_images(
            anchor_result['image_url'],
            skp_result['image_url']
        )
        print(f"Vision result: {vision_result}")
    except Exception as e:
        print(f"Vision error: {e}")
else:
    print("Cannot test image comparison - missing image URLs")