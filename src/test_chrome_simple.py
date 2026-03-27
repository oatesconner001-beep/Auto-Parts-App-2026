#!/usr/bin/env python3
"""
Simple Chrome worker test to verify basic functionality.
"""

import tempfile
from pathlib import Path

def test_chrome_worker():
    """Test basic Chrome worker functionality."""
    print("Testing Chrome Worker...")

    try:
        from chrome_worker import ChromeWorker

        # Create test worker
        profile_dir = str(Path(tempfile.gettempdir()) / "test_chrome_worker")
        worker = ChromeWorker("test", profile_dir)

        print("Chrome worker created successfully")

        # Try to initialize
        if worker.initialize():
            print("Chrome worker initialized successfully!")

            # Try health check
            if worker.health_check():
                print("Health check passed!")
            else:
                print("Health check failed")

            # Cleanup
            worker.cleanup()
            print("Worker cleaned up")
            return True
        else:
            print("Chrome worker failed to initialize")
            return False

    except Exception as e:
        print(f"Chrome worker test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_chrome_worker()
    print(f"Test result: {'PASS' if success else 'FAIL'}")