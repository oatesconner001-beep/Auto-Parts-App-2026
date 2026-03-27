#!/usr/bin/env python3
"""Check image availability for UNCERTAIN rows."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from scraper_subprocess import scrape_rockauto_subprocess as scrape_rockauto

# Test a few UNCERTAIN rows from our debug output
test_pairs = [
    ("9415", "SKM9411"),  # Row 67
    ("3503", "SKM3503"),  # Row 151
    ("2564", "SKM2564"),  # Row 189
    ("3157", "SKM3157"),  # Row 233
    ("9158", "SKM9158"),  # Row 265
]

print("Checking image availability for UNCERTAIN rows...\n")

both_images = 0
missing_images = 0

for anchor_part, skp_part in test_pairs:
    print(f"Testing ANCHOR {anchor_part} vs SKP {skp_part}")

    try:
        anchor_result = scrape_rockauto(anchor_part, "ANCHOR")
        skp_result = scrape_rockauto(skp_part, "SKP")

        anchor_img = anchor_result.get('image_url')
        skp_img = skp_result.get('image_url')

        print(f"  ANCHOR image: {'YES' if anchor_img else 'NO'}")
        print(f"  SKP image:    {'YES' if skp_img else 'NO'}")

        if anchor_img and skp_img:
            both_images += 1
            print(f"  -> CAN compare images")
        else:
            missing_images += 1
            print(f"  -> CANNOT compare (missing image)")

    except Exception as e:
        print(f"  -> ERROR: {e}")
        missing_images += 1

    print()

print(f"SUMMARY:")
print(f"  Rows with both images: {both_images}")
print(f"  Rows missing images:   {missing_images}")
print(f"  Image comparison rate: {both_images}/{both_images + missing_images} ({100 * both_images / (both_images + missing_images):.1f}%)")