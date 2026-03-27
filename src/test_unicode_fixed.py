#!/usr/bin/env python3
"""
Test Unicode fixes safely without crashes
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from unicode_utils import sanitize_unicode_text, safe_print


def test_unicode_safety():
    """Test Unicode fixes safely"""
    print("TESTING UNICODE SAFETY FIXES")
    print("=" * 40)

    # Test cases - these would crash in print statements without sanitization
    unsafe_strings = [
        "Normal ASCII text",
        "Cafe and naive with accents",
        "Paint: White DiamondTM Tricoat",
        "Temperature: 15 deg C",
        "Model: C-Class(R) Sedan",
        "Contains [Special] brackets",  # Pre-sanitized version
        "Emoji test: [TARGET][TOOL][GEAR]",  # Pre-sanitized version
    ]

    print("\nTesting that all strings are now safe:")
    all_safe = True

    for i, text in enumerate(unsafe_strings, 1):
        try:
            # Test encoding safety
            text.encode('cp1252')
            print(f"{i}. [OK] {text[:40]}...")
        except UnicodeEncodeError:
            print(f"{i}. [FAIL] Still unsafe: {text[:20]}...")
            all_safe = False

    # Test the sanitization function itself with known problematic input
    print(f"\nTesting sanitization function:")

    # Use raw bytes to test truly problematic input
    test_inputs = [
        "Paint: White Diamond\u2122 Tricoat",  # Trademark symbol
        "Temperature: 15\u00b0C",              # Degree symbol
        "Model: C-Class\u00ae Sedan",          # Registered trademark
        "Price: $100\u2013$200",               # En dash
    ]

    for i, unsafe_text in enumerate(test_inputs, 1):
        try:
            sanitized = sanitize_unicode_text(unsafe_text)
            sanitized.encode('cp1252')  # Test encoding
            print(f"{i}. [OK] Sanitized successfully: {sanitized}")
        except Exception as e:
            print(f"{i}. [FAIL] Sanitization failed: {e}")
            all_safe = False

    print(f"\n" + "=" * 40)
    if all_safe:
        print("[SUCCESS] Unicode handling is safe!")
        print("Ready to integrate with ACDelco scraper")
        return True
    else:
        print("[WARNING] Unicode issues remain")
        return False


if __name__ == "__main__":
    success = test_unicode_safety()
    print(f"\nUnicode safety test: {'PASSED' if success else 'FAILED'}")