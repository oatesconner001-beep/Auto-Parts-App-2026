#!/usr/bin/env python3
"""
Simple progress monitor for the Anchor run.
Usage: uv run python monitor_anchor.py
"""

import re
import time
from datetime import datetime

def check_progress():
    try:
        with open('output/run_anchor.txt', 'r') as f:
            content = f.read()

        # Extract current progress
        progress_matches = re.findall(r'\[(\d+)/495\]', content)
        if progress_matches:
            current = int(progress_matches[-1])
            percent = round(current / 495 * 100, 1)
            remaining = 495 - current
            est_minutes = remaining * 2.5 / 60 + remaining * 1 / 60

            print(f"{datetime.now().strftime('%H:%M:%S')} | Progress: {current}/495 ({percent}%) | ETA: ~{int(est_minutes)}m")

            # Check if completed
            if current >= 495:
                print("🎉 ANCHOR RUN COMPLETED!")
                return True

        else:
            print(f"{datetime.now().strftime('%H:%M:%S')} | Status: Unable to read progress")

    except Exception as e:
        print(f"{datetime.now().strftime('%H:%M:%S')} | Error: {e}")

    return False

if __name__ == "__main__":
    print("=== Monitoring Anchor Run (Ctrl+C to stop) ===")

    try:
        while True:
            completed = check_progress()
            if completed:
                break
            time.sleep(60)  # Check every minute

    except KeyboardInterrupt:
        print("\nMonitoring stopped.")