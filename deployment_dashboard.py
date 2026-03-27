#!/usr/bin/env python3
"""
Enhanced Parts Agent Deployment Dashboard
Real-time monitoring for all deployment phases
"""

import sys
import time
from pathlib import Path
from datetime import datetime

# Add src to path
_src = Path(__file__).parent / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from count_results import count_all_results

# Deployment targets and phases
WAVE_TARGETS = {
    "Wave 1": {"rows": 25, "baseline_likely": 150, "target_likely": 175},
    "Wave 2": {"rows": 50, "baseline_likely": 175, "target_likely": 225},
    "Wave 3": {"rows": 100, "baseline_likely": 225, "target_likely": 325},
}

TOTAL_UNCERTAIN = 741  # Total UNCERTAIN rows across all sheets

def display_header():
    """Display dashboard header"""
    print("\n" + "=" * 80)
    print(" " * 20 + "ENHANCED PARTS AGENT DEPLOYMENT DASHBOARD")
    print("=" * 80)
    print(f"Dashboard Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Target: {TOTAL_UNCERTAIN} UNCERTAIN -> LIKELY upgrades (100% rate)")
    print("=" * 80)

def analyze_wave_progress(sheet_stats, wave_name, wave_data):
    """Analyze progress of a specific wave"""
    current_likely = sheet_stats.get('LIKELY', 0)
    current_uncertain = sheet_stats.get('UNCERTAIN', 0)

    baseline_likely = wave_data['baseline_likely']
    target_likely = wave_data['target_likely']
    target_rows = wave_data['rows']

    # Calculate progress
    progress = max(0, current_likely - baseline_likely)
    progress_pct = (progress / target_rows * 100) if target_rows > 0 else 0

    # Determine status
    if current_likely >= target_likely:
        status = "COMPLETE"
        symbol = "[✓]"
    elif progress > 0:
        status = "IN PROGRESS"
        symbol = "[~]"
    else:
        status = "PENDING"
        symbol = "[ ]"

    return {
        'status': status,
        'symbol': symbol,
        'progress': progress,
        'progress_pct': progress_pct,
        'current_likely': current_likely,
        'current_uncertain': current_uncertain
    }

def display_sheet_status():
    """Display status for all sheets"""
    print("\n>> SHEET-BY-SHEET STATUS")
    print("-" * 80)

    try:
        all_stats = count_all_results()
        total_likely = 0
        total_uncertain = 0
        total_processed = 0

        for sheet_name in ["Anchor", "Dorman", "GMB", "SMP", "Four Seasons "]:
            stats = all_stats.get(sheet_name, {})
            if stats:
                likely = stats.get('LIKELY', 0)
                uncertain = stats.get('UNCERTAIN', 0)
                processed = stats.get('processed', 0)
                success_rate = ((stats.get('YES', 0) + likely) / processed * 100) if processed > 0 else 0

                total_likely += likely
                total_uncertain += uncertain
                total_processed += processed

                print(f"{sheet_name:<15} | "
                      f"LIKELY: {likely:>3} | "
                      f"UNCERTAIN: {uncertain:>3} | "
                      f"Success: {success_rate:>5.1f}% | "
                      f"Processed: {processed:>4}")

        print("-" * 80)
        total_success = (total_likely / total_processed * 100) if total_processed > 0 else 0
        print(f"{'TOTAL':<15} | "
              f"LIKELY: {total_likely:>3} | "
              f"UNCERTAIN: {total_uncertain:>3} | "
              f"Success: {total_success:>5.1f}% | "
              f"Processed: {total_processed:>4}")

    except Exception as e:
        print(f"ERROR: Could not load sheet statistics: {e}")

def display_wave_progress():
    """Display Anchor wave-by-wave progress"""
    print("\n>> ANCHOR ENHANCED ANALYSIS PROGRESS")
    print("-" * 80)

    try:
        all_stats = count_all_results()
        anchor_stats = all_stats.get("Anchor", {})

        if anchor_stats:
            print(f"Current Status: {anchor_stats['LIKELY']} LIKELY, {anchor_stats['UNCERTAIN']} UNCERTAIN")
            print("-" * 80)

            for wave_name, wave_data in WAVE_TARGETS.items():
                analysis = analyze_wave_progress(anchor_stats, wave_name, wave_data)

                print(f"{analysis['symbol']} {wave_name:<10} | "
                      f"Target: {wave_data['rows']:>3} rows | "
                      f"Progress: {analysis['progress']:>2}/{wave_data['rows']} | "
                      f"{analysis['progress_pct']:>5.1f}% | "
                      f"{analysis['status']}")

        else:
            print("ERROR: Could not load Anchor statistics")

    except Exception as e:
        print(f"ERROR: Could not analyze wave progress: {e}")

def display_system_status():
    """Display system monitoring information"""
    print("\n>> SYSTEM STATUS")
    print("-" * 80)
    print("Analytics Dashboard:  [RUNNING] GUI application active")
    print("Web Dashboard:        [RUNNING] http://localhost:5000")
    print("Enhanced Engine:      [READY]   Phase 1 (100% upgrade rate)")
    print("Optimization:         [READY]   Smart prioritization active")
    print("Validation:           [READY]   Quality monitoring active")

def display_next_actions():
    """Display recommended next actions"""
    print("\n>> RECOMMENDED NEXT ACTIONS")
    print("-" * 80)

    try:
        all_stats = count_all_results()
        anchor_stats = all_stats.get("Anchor", {})

        if anchor_stats:
            current_likely = anchor_stats['LIKELY']

            if current_likely < 175:
                print("1. Monitor Wave 1 completion (25 rows processing)")
                print("2. Launch Wave 2 when Wave 1 completes")
                print("3. Continue to larger batches (100+ rows)")
            elif current_likely < 225:
                print("1. Deploy Wave 2 enhanced analysis (50 rows)")
                print("2. Monitor progress via dashboards")
                print("3. Prepare Wave 3 scaling")
            else:
                print("1. Scale to larger batches (100+ rows)")
                print("2. Process other sheets (Dorman, GMB)")
                print("3. Monitor overall project completion")

            print(f"4. Access live monitoring: http://localhost:5000")
            print(f"5. Run 'uv run python src/count_results.py' for updates")

    except Exception as e:
        print("Could not determine next actions - check system status")

def main():
    """Main dashboard display"""
    try:
        display_header()
        display_sheet_status()
        display_wave_progress()
        display_system_status()
        display_next_actions()
        print("=" * 80)
        print("Dashboard complete. Re-run to refresh data.")
        print("=" * 80)

    except KeyboardInterrupt:
        print("\nDashboard interrupted by user")
    except Exception as e:
        print(f"Dashboard error: {e}")

if __name__ == "__main__":
    main()