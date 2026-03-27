#!/usr/bin/env python3
"""
Wave 2 Enhanced Analysis Deployment Script
Auto-launches Wave 2 (50 rows) when Wave 1 completes
"""

import sys
import time
import subprocess
from pathlib import Path
from datetime import datetime

# Add src to path
_src = Path(__file__).parent / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from count_results import count_all_results

def check_wave1_completion():
    """Check if Wave 1 has completed by monitoring LIKELY count increase"""

    print("=" * 60)
    print(">> WAVE 2 AUTO-DEPLOYMENT - Monitoring Wave 1")
    print("=" * 60)
    print(f"Monitoring started: {datetime.now().strftime('%H:%M:%S')}")
    print("Baseline: 150 LIKELY, 412 UNCERTAIN")
    print("Wave 1 target: 175 LIKELY, 387 UNCERTAIN (+25 upgrades)")
    print("=" * 60)

    baseline_likely = 150
    target_likely = 175

    while True:
        try:
            # Get current stats
            all_stats = count_all_results()
            anchor_stats = all_stats.get("Anchor", {})

            if anchor_stats:
                current_likely = anchor_stats['LIKELY']
                current_uncertain = anchor_stats['UNCERTAIN']

                print(f"{datetime.now().strftime('%H:%M:%S')} | "
                      f"LIKELY: {current_likely} | UNCERTAIN: {current_uncertain}")

                # Check if Wave 1 completed
                if current_likely >= target_likely:
                    upgrade_count = current_likely - baseline_likely
                    print("=" * 60)
                    print(f">> WAVE 1 COMPLETE! +{upgrade_count} LIKELY upgrades detected")
                    print(f">> Current: {current_likely} LIKELY, {current_uncertain} UNCERTAIN")
                    print(">> Deploying Wave 2 in 30 seconds...")
                    print("=" * 60)

                    time.sleep(30)
                    return True

            time.sleep(60)  # Check every minute

        except Exception as e:
            print(f"ERROR: {e}")
            time.sleep(60)

def deploy_wave2():
    """Deploy Wave 2 enhanced analysis (50 rows)"""

    print("=" * 60)
    print(">> DEPLOYING WAVE 2 ENHANCED ANALYSIS")
    print("=" * 60)
    print(f"Target: 50 Anchor UNCERTAIN -> LIKELY upgrades")
    print(f"Expected processing time: ~28 minutes")
    print(f"Starting: {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 60)

    # Change to project directory
    project_dir = Path(__file__).parent

    # Set environment and run Wave 2
    env = {
        "PATH": str(Path.home() / ".local" / "bin") + ":" + str(Path("/c/Users/Owner/.local/bin")) + ":" + os.environ.get("PATH", ""),
        **os.environ
    }

    cmd = [
        "uv", "run", "python",
        "src/run_enhanced_image_analysis.py",
        "Anchor", "--limit", "50"
    ]

    # Log command and start
    print(f"Command: {' '.join(cmd)}")
    print(f"Directory: {project_dir}")
    print("=" * 60)

    subprocess.run(cmd, cwd=project_dir, env=env)

if __name__ == "__main__":
    import os

    print(">> Wave 2 Auto-Deployment System Starting...")

    # Monitor Wave 1 completion
    if check_wave1_completion():
        # Deploy Wave 2
        deploy_wave2()
        print(">> Wave 2 deployment initiated!")
    else:
        print(">> Wave 1 monitoring failed - manual intervention required")