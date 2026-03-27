#!/usr/bin/env python3
"""
Parts Agent Pro — Unified Desktop Application
Main entry point for the enhanced GUI application.

Usage:
    python main_app.py

or with uv:
    uv run python main_app.py
"""

import sys
import os
from pathlib import Path

# Add src directory to Python path
src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))

def main():
    """Main entry point for the unified Parts Agent application."""
    print("Starting Parts Agent Pro...")

    try:
        # Import and run the main GUI
        from gui.main_window import UnifiedPartsAgent

        print("Launching unified GUI interface...")
        app = UnifiedPartsAgent()
        app.mainloop()

    except ImportError as e:
        print(f"Import error: {e}")
        print("Please ensure all required modules are available.")
        print("Run 'uv sync' to install dependencies if needed.")
        sys.exit(1)
    except Exception as e:
        print(f"Failed to start application: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()