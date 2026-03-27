#!/usr/bin/env python3
"""
Unicode handling utilities for scraper system
Ensures all text data can be safely stored and displayed without crashes
"""

import re
import unicodedata
from typing import Any, Dict, List, Optional


def sanitize_unicode_text(text: str, replacement: str = '') -> str:
    """Sanitize Unicode text to prevent encoding crashes

    Args:
        text: Input text that may contain problematic Unicode characters
        replacement: Character to replace problematic chars with (default: remove)

    Returns:
        str: Sanitized text safe for Windows cp1252 encoding
    """
    if not text or not isinstance(text, str):
        return str(text) if text is not None else ''

    try:
        # Step 1: Normalize Unicode to decomposed form
        text = unicodedata.normalize('NFKD', text)

        # Step 2: Handle common problematic characters first
        char_replacements = {
            '™': 'TM',           # Trademark symbol
            '®': '(R)',          # Registered trademark
            '©': '(C)',          # Copyright symbol
            '°': ' deg ',        # Degree symbol
            '—': ' - ',          # Em dash
            '–': ' - ',          # En dash
            ''': "'",            # Smart quote
            ''': "'",            # Smart quote
            '"': '"',            # Smart quote
            '"': '"',            # Smart quote
            '…': '...',          # Ellipsis
            '【': '[',           # Special bracket
            '】': ']',           # Special bracket
            '🎯': '[TARGET]',    # Target emoji
            '🔧': '[TOOL]',      # Tool emoji
            '⚙️': '[GEAR]',      # Gear emoji
        }

        for unicode_char, replacement_text in char_replacements.items():
            text = text.replace(unicode_char, replacement_text)

        # Step 3: Remove or replace remaining problematic Unicode
        sanitized_chars = []
        for char in text:
            try:
                # Test if character can be encoded in cp1252 (Windows default)
                char.encode('cp1252')
                sanitized_chars.append(char)
            except UnicodeEncodeError:
                # Handle by Unicode category
                category = unicodedata.category(char)

                if category.startswith('C'):  # Control characters
                    sanitized_chars.append(replacement)
                elif category.startswith('S') and ord(char) > 255:  # Extended symbols
                    sanitized_chars.append(replacement)
                elif ord(char) > 255:  # Extended Unicode
                    # Try to find ASCII equivalent through decomposition
                    decomposed = unicodedata.normalize('NFKD', char)
                    ascii_equivalent = ''.join(c for c in decomposed if ord(c) < 128)
                    sanitized_chars.append(ascii_equivalent if ascii_equivalent else replacement)
                else:
                    # Keep basic extended ASCII (128-255)
                    sanitized_chars.append(char)

        # Step 4: Clean up multiple spaces and trim
        result = ''.join(sanitized_chars)
        result = re.sub(r'\s+', ' ', result).strip()

        # Step 5: Final safety check - ensure result can be encoded
        result.encode('cp1252')
        return result

    except Exception as e:
        # Ultimate fallback: keep only basic ASCII (0-127)
        safe_text = ''.join(char for char in str(text) if 0 <= ord(char) <= 127)
        return re.sub(r'\s+', ' ', safe_text).strip()


def sanitize_unicode_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively sanitize all string values in a dictionary

    Args:
        data: Dictionary that may contain Unicode strings

    Returns:
        Dict: Dictionary with all strings sanitized
    """
    if not isinstance(data, dict):
        return data

    sanitized = {}
    for key, value in data.items():
        # Sanitize the key itself
        clean_key = sanitize_unicode_text(str(key))

        # Sanitize the value based on its type
        if isinstance(value, str):
            sanitized[clean_key] = sanitize_unicode_text(value)
        elif isinstance(value, dict):
            sanitized[clean_key] = sanitize_unicode_dict(value)
        elif isinstance(value, list):
            sanitized[clean_key] = sanitize_unicode_list(value)
        else:
            sanitized[clean_key] = value

    return sanitized


def sanitize_unicode_list(data: List[Any]) -> List[Any]:
    """Recursively sanitize all string values in a list

    Args:
        data: List that may contain Unicode strings

    Returns:
        List: List with all strings sanitized
    """
    if not isinstance(data, list):
        return data

    sanitized = []
    for item in data:
        if isinstance(item, str):
            sanitized.append(sanitize_unicode_text(item))
        elif isinstance(item, dict):
            sanitized.append(sanitize_unicode_dict(item))
        elif isinstance(item, list):
            sanitized.append(sanitize_unicode_list(item))
        else:
            sanitized.append(item)

    return sanitized


def safe_print(text: str, prefix: str = '') -> None:
    """Safely print text without Unicode crashes

    Args:
        text: Text to print (may contain Unicode)
        prefix: Optional prefix for the message
    """
    try:
        safe_text = sanitize_unicode_text(str(text))
        if prefix:
            print(f"{prefix} {safe_text}")
        else:
            print(safe_text)
    except Exception as e:
        print(f"[PRINT ERROR] {e}")


def test_unicode_sanitization():
    """Test the Unicode sanitization functions"""
    print("TESTING UNICODE SANITIZATION")
    print("=" * 40)

    test_strings = [
        "Normal ASCII text",
        "Café and naïve with accents",  # Accented characters
        "Paint: White Diamond™ Tricoat",  # Trademark symbol
        "Temperature: 15°C to 85°C",  # Degree symbol
        "Price: $99.99 — Special Offer!",  # Em dash
        "Model: C-Class® Sedan",  # Registered trademark
        "Contains 【Special】 brackets",  # Special Unicode brackets
        "Emoji test: 🎯🔧⚙️",  # Emojis that caused the crash
    ]

    for i, test_string in enumerate(test_strings, 1):
        try:
            print(f"\nTest {i}: {test_string[:30]}...")
            sanitized = sanitize_unicode_text(test_string)
            print(f"  Original length: {len(test_string)}")
            print(f"  Sanitized: '{sanitized}'")
            print(f"  Sanitized length: {len(sanitized)}")

            # Test if it can be encoded safely
            sanitized.encode('cp1252')
            print(f"  [OK] Safe for cp1252 encoding")

        except Exception as e:
            print(f"  [ERROR] Failed: {e}")

    print(f"\nUnicode sanitization test complete!")


if __name__ == "__main__":
    test_unicode_sanitization()