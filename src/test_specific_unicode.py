#!/usr/bin/env python3
"""
Test specific Unicode issues that caused crashes
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from unicode_utils import sanitize_unicode_text


def test_crash_cases():
    """Test the specific cases that caused crashes"""
    print("TESTING SPECIFIC UNICODE CRASH CASES")
    print("=" * 50)

    # Test cases that caused issues
    crash_test_cases = [
        "Contains 【Special】 brackets",  # Special Unicode brackets
        "Emoji test: 🎯🔧⚙️",           # Emojis that caused the original crash
        "Paint: White Diamond™ Tricoat",  # Trademark symbol
        "Temperature: 15°C",              # Degree symbol
        "Model: C-Class® Sedan",          # Registered trademark
        "Price range: $100–$200",         # En dash
        "Description — special details",   # Em dash
    ]

    all_passed = True

    for i, test_case in enumerate(crash_test_cases, 1):
        print(f"\nTest {i}: {test_case}")
        try:
            # Test original string encoding
            try:
                test_case.encode('cp1252')
                print("  Original: [OK] Already safe")
            except UnicodeEncodeError:
                print("  Original: [FAIL] Would crash")

            # Test sanitized version
            sanitized = sanitize_unicode_text(test_case)
            print(f"  Sanitized: '{sanitized}'")

            # Test if sanitized version is safe
            try:
                sanitized.encode('cp1252')
                print("  Encoding: [OK] Safe for cp1252")
            except UnicodeEncodeError as e:
                print(f"  Encoding: [FAIL] Still unsafe: {e}")
                all_passed = False

        except Exception as e:
            print(f"  [ERROR] Test failed: {e}")
            all_passed = False

    print(f"\n" + "=" * 50)
    if all_passed:
        print("✓ ALL UNICODE TESTS PASSED")
        print("Unicode sanitization is working correctly")
    else:
        print("✗ SOME TESTS FAILED")
        print("Unicode sanitization needs more work")

    return all_passed


if __name__ == "__main__":
    success = test_crash_cases()
    if success:
        print("\nReady to apply Unicode fixes to ACDelco scraper!")
    else:
        print("\nNeed to fix Unicode sanitization first!")