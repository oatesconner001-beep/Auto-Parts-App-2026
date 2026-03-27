#!/usr/bin/env python3
"""
Subprocess-isolated scraper wrapper for scraper_local.py.

This solves asyncio event loop conflicts by running the Chrome scraper
in a completely separate process, avoiding any async/sync API conflicts.
"""

import json
import subprocess
import sys
import os
from pathlib import Path

def scrape_rockauto_subprocess(part_number: str, brand: str) -> dict:
    """
    Run scraper_local.py in a subprocess to avoid asyncio conflicts.

    Returns the same dict format as scraper_local.scrape_rockauto().
    """
    try:
        # Create script content that outputs clean JSON
        import json as _json
        _pn_safe = _json.dumps(part_number)
        _br_safe = _json.dumps(brand)

        script_content = f'''
import sys
import os
import json
from io import StringIO

# Add project path
sys.path.append(r"{Path(__file__).parent}")

# Capture stdout to suppress debug output
old_stdout = sys.stdout
sys.stdout = StringIO()

try:
    from scraper_local import scrape_rockauto
    result = scrape_rockauto({_pn_safe}, {_br_safe})

    # Restore stdout and output clean JSON
    sys.stdout = old_stdout
    print(json.dumps(result, ensure_ascii=True))

except Exception as e:
    # Restore stdout for error output
    sys.stdout = old_stdout
    error_result = {{
        "found": False,
        "error": str(e),
        "category": None,
        "oem_refs": [],
        "price": None,
        "moreinfo_url": None,
        "image_url": None,
        "specs": None,
        "description": None,
        "features": None,
        "warranty": None,
    }}
    print(json.dumps(error_result, ensure_ascii=True))
'''

        # Set up environment
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUNBUFFERED"] = "1"

        # Run the script in subprocess
        result = subprocess.run([
            sys.executable, "-c", script_content
        ], capture_output=True, text=True, timeout=90,
        cwd=str(Path(__file__).parent.parent), env=env)

        # Parse the JSON output
        if result.stdout.strip():
            try:
                return json.loads(result.stdout.strip())
            except json.JSONDecodeError as e:
                return {
                    "found": False,
                    "error": f"JSON parse error: {e}. Output: {result.stdout[:200]}",
                    "category": None,
                    "oem_refs": [],
                    "price": None,
                    "moreinfo_url": None,
                    "image_url": None,
                    "specs": None,
                    "description": None,
                    "features": None,
                    "warranty": None,
                }
        else:
            return {
                "found": False,
                "error": f"No output. Return code: {result.returncode}. Stderr: {result.stderr[:200]}",
                "category": None,
                "oem_refs": [],
                "price": None,
                "moreinfo_url": None,
                "image_url": None,
                "specs": None,
                "description": None,
                "features": None,
                "warranty": None,
            }

    except subprocess.TimeoutExpired:
        return {
            "found": False,
            "error": "Subprocess timeout (>45s)",
            "category": None,
            "oem_refs": [],
            "price": None,
            "moreinfo_url": None,
            "image_url": None,
            "specs": None,
            "description": None,
            "features": None,
            "warranty": None,
        }
    except Exception as e:
        return {
            "found": False,
            "error": f"Subprocess exception: {e}",
            "category": None,
            "oem_refs": [],
            "price": None,
            "moreinfo_url": None,
            "image_url": None,
            "specs": None,
            "description": None,
            "features": None,
            "warranty": None,
        }

if __name__ == "__main__":
    # Test the subprocess scraper
    print("=== Testing Subprocess Scraper ===")
    result = scrape_rockauto_subprocess("3217", "ANCHOR")
    print(json.dumps(result, indent=2))