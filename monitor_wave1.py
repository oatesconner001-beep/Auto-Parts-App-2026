#!/usr/bin/env python3
"""
Monitor Wave 1 Enhanced Analysis Progress
Real-time tracking of UNCERTAIN -> LIKELY upgrades
"""

import sys
from pathlib import Path
import time
from datetime import datetime

# Add src to path
_src = Path(__file__).parent / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from count_results import count_all_results

def monitor_progress():
    """Monitor Wave 1 progress with before/after comparison"""

    print("=" * 60)
    print(">> WAVE 1 ENHANCED ANALYSIS - Progress Monitor")
    print("=" * 60)
    print(f"Target: 25 Anchor UNCERTAIN -> LIKELY upgrades (100% rate)")
    print(f"Monitoring started: {datetime.now().strftime('%H:%M:%S')}")
    print()

    try:
        # Get current stats for all sheets
        all_stats = count_all_results()
        anchor_stats = all_stats.get("Anchor", {})

        if anchor_stats:
            processed = anchor_stats['processed']
            likely = anchor_stats['LIKELY']
            uncertain = anchor_stats['UNCERTAIN']
            confirmed = anchor_stats['YES'] + likely
            success_rate = (confirmed / processed * 100) if processed > 0 else 0

            print(f">> Current Anchor Status:")
            print(f"   Total Processed: {processed}")
            print(f"   LIKELY matches: {likely}")
            print(f"   UNCERTAIN remaining: {uncertain}")
            print(f"   Success rate: {success_rate:.1f}%")
            print()

            print(f">> Wave 1 Expected Outcome:")
            print(f"   Before: {likely} LIKELY + {uncertain} UNCERTAIN")
            expected_after_likely = likely + 25
            expected_after_uncertain = max(0, uncertain - 25)
            expected_success = (confirmed + 25) / processed * 100 if processed > 0 else 0
            print(f"   After: {expected_after_likely} LIKELY + {expected_after_uncertain} UNCERTAIN")
            print(f"   New Success Rate: {expected_success:.1f}%")

        else:
            print("ERROR: Could not load Anchor stats")

    except Exception as e:
        print(f"ERROR: Error monitoring progress: {e}")

    print("=" * 60)
    print(">> Monitor setup complete")
    print("Use 'uv run python src/count_results.py' to check live updates")
    print("=" * 60)

if __name__ == "__main__":
    monitor_progress()