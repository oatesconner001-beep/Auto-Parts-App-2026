#!/usr/bin/env python3
"""Simple test script to isolate Chrome scraper issues."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

print("Testing scraper_subprocess...")

try:
    from scraper_subprocess import scrape_rockauto_subprocess as scrape_rockauto
    print("Import successful")

    print("Testing simple scrape...")
    result = scrape_rockauto("3217", "ANCHOR")
    print(f"Result: {result}")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()