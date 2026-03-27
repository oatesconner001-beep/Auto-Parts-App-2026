#!/usr/bin/env python3
"""
Quick test of the AI comparison module.
Run this after adding Anthropic API credits.
"""

from src.ai_compare import compare_parts

# Test data from the confirmed working case
anchor_data = {
    "part_number": "3217",
    "brand": "ANCHOR",
    "found": True,
    "category": "Motor Mount",
    "oem_refs": ["5273883AD", "7B0199279A"],
    "price": "$20.79",
    "description": "Anchor Industries Motor Mount",
    "features": ["Natural rubber", "Heat treated bolts"],
    "specs": {"Mounting Hardware Included": "No"},
    "warranty": "12 Months"
}

skp_data = {
    "part_number": "SKM3217",
    "brand": "SKP",
    "found": True,
    "category": "Motor Mount",
    "oem_refs": ["5273883AC", "5273883AD", "7B0199279"],
    "price": "$14.03",
    "description": "SKP Motor Mount",
    "features": ["Natural rubber", "Heat treated bolts"],
    "specs": {},
    "warranty": "12 Months"
}

print("Testing AI comparison with shared OEM ref 5273883AD...")
result = compare_parts(anchor_data, skp_data, "ENGINE MOUNT")

print("\nAI Result:")
for key, value in result.items():
    print(f"  {key}: {value}")

print(f"\nExpected: YES/LIKELY match due to shared OEM ref '5273883AD'")