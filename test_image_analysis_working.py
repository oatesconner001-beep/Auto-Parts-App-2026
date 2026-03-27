#!/usr/bin/env python3
"""Test image analysis on rows with confirmed image availability."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from local_vision import compare_images

# Test the 3 rows that have both images
working_pairs = [
    ("9415", "SKM9411", "https://www.rockauto.com/info/28/9415-000.jpg"),  # Will get actual URLs
    ("2564", "SKM2564", ""),
    ("3157", "SKM3157", ""),
]

print("Testing image analysis on confirmed image pairs...\n")

for i, (anchor_part, skp_part, _) in enumerate(working_pairs, 1):
    print(f"[{i}/3] Testing ANCHOR {anchor_part} vs SKP {skp_part}")

    try:
        from scraper_subprocess import scrape_rockauto_subprocess as scrape_rockauto

        # Get actual image URLs
        anchor_result = scrape_rockauto(anchor_part, "ANCHOR")
        skp_result = scrape_rockauto(skp_part, "SKP")

        anchor_url = anchor_result.get('image_url')
        skp_url = skp_result.get('image_url')

        if anchor_url and skp_url:
            print(f"  Images confirmed - running comparison...")

            # Run actual image comparison
            vision_result = compare_images(anchor_url, skp_url, f"ENGINE MOUNT")

            print(f"  Result: {vision_result}")

        else:
            print(f"  Skipping - missing image URLs")

    except Exception as e:
        print(f"  ERROR: {e}")

    print()

print("Image analysis test completed!")