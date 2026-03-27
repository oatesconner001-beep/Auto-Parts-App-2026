#!/usr/bin/env python3
"""
Deployment Metrics Tracker
Captures before/after statistics for enhancement impact analysis
"""

import sys
import json
import time
from pathlib import Path
from datetime import datetime

# Add src to path
_src = Path(__file__).parent / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))

from count_results import count_all_results

METRICS_FILE = Path(__file__).parent / "deployment_metrics.json"

def capture_baseline():
    """Capture baseline metrics before enhancement deployment"""

    print(">> Capturing Baseline Deployment Metrics")
    print("=" * 60)

    try:
        all_stats = count_all_results()

        baseline_data = {
            "timestamp": datetime.now().isoformat(),
            "phase": "baseline",
            "description": "Pre-enhancement deployment baseline",
            "sheets": all_stats,
            "summary": {
                "total_processed": sum(sheet.get('processed', 0) for sheet in all_stats.values()),
                "total_likely": sum(sheet.get('LIKELY', 0) for sheet in all_stats.values()),
                "total_uncertain": sum(sheet.get('UNCERTAIN', 0) for sheet in all_stats.values()),
                "anchor_likely": all_stats.get("Anchor", {}).get('LIKELY', 0),
                "anchor_uncertain": all_stats.get("Anchor", {}).get('UNCERTAIN', 0)
            }
        }

        # Load existing metrics or create new
        if METRICS_FILE.exists():
            with open(METRICS_FILE, 'r') as f:
                metrics = json.load(f)
        else:
            metrics = {"deployment_history": []}

        # Add baseline data
        metrics["deployment_history"].append(baseline_data)

        # Save updated metrics
        with open(METRICS_FILE, 'w') as f:
            json.dump(metrics, f, indent=2)

        print(f"[OK] Baseline captured at {baseline_data['timestamp']}")
        print(f"  Total LIKELY: {baseline_data['summary']['total_likely']}")
        print(f"  Total UNCERTAIN: {baseline_data['summary']['total_uncertain']}")
        print(f"  Anchor LIKELY: {baseline_data['summary']['anchor_likely']}")
        print(f"  Anchor UNCERTAIN: {baseline_data['summary']['anchor_uncertain']}")
        print(f"[OK] Metrics saved to: {METRICS_FILE}")

        return baseline_data

    except Exception as e:
        print(f"ERROR: Could not capture baseline metrics: {e}")
        return None

def capture_wave_completion(wave_name, target_upgrades):
    """Capture metrics after a wave completes"""

    print(f">> Capturing {wave_name} Completion Metrics")
    print("=" * 60)

    try:
        all_stats = count_all_results()

        completion_data = {
            "timestamp": datetime.now().isoformat(),
            "phase": f"{wave_name}_completion",
            "description": f"{wave_name} enhanced analysis completion",
            "target_upgrades": target_upgrades,
            "sheets": all_stats,
            "summary": {
                "total_processed": sum(sheet.get('processed', 0) for sheet in all_stats.values()),
                "total_likely": sum(sheet.get('LIKELY', 0) for sheet in all_stats.values()),
                "total_uncertain": sum(sheet.get('UNCERTAIN', 0) for sheet in all_stats.values()),
                "anchor_likely": all_stats.get("Anchor", {}).get('LIKELY', 0),
                "anchor_uncertain": all_stats.get("Anchor", {}).get('UNCERTAIN', 0)
            }
        }

        # Load existing metrics
        if METRICS_FILE.exists():
            with open(METRICS_FILE, 'r') as f:
                metrics = json.load(f)
        else:
            metrics = {"deployment_history": []}

        # Add completion data
        metrics["deployment_history"].append(completion_data)

        # Calculate impact vs baseline
        baseline = next((h for h in reversed(metrics["deployment_history"]) if h["phase"] == "baseline"), None)
        if baseline:
            impact = {
                "likely_increase": completion_data["summary"]["anchor_likely"] - baseline["summary"]["anchor_likely"],
                "uncertain_decrease": baseline["summary"]["anchor_uncertain"] - completion_data["summary"]["anchor_uncertain"],
                "success_rate_improvement": f"{completion_data['summary']['anchor_likely'] / 590 * 100:.1f}% vs {baseline['summary']['anchor_likely'] / 590 * 100:.1f}%"
            }
            completion_data["impact_vs_baseline"] = impact

        # Save updated metrics
        with open(METRICS_FILE, 'w') as f:
            json.dump(metrics, f, indent=2)

        print(f"[OK] {wave_name} metrics captured at {completion_data['timestamp']}")
        print(f"  Anchor LIKELY: {completion_data['summary']['anchor_likely']}")
        print(f"  Anchor UNCERTAIN: {completion_data['summary']['anchor_uncertain']}")

        if "impact_vs_baseline" in completion_data:
            impact = completion_data["impact_vs_baseline"]
            print(f"  Impact: +{impact['likely_increase']} LIKELY, -{impact['uncertain_decrease']} UNCERTAIN")
            print(f"  Success Rate: {impact['success_rate_improvement']}")

        print(f"[OK] Metrics saved to: {METRICS_FILE}")

        return completion_data

    except Exception as e:
        print(f"ERROR: Could not capture {wave_name} metrics: {e}")
        return None

def display_deployment_progress():
    """Display deployment progress from metrics"""

    if not METRICS_FILE.exists():
        print("No deployment metrics available yet.")
        return

    try:
        with open(METRICS_FILE, 'r') as f:
            metrics = json.load(f)

        print(">> Deployment Progress History")
        print("=" * 60)

        for entry in metrics["deployment_history"]:
            timestamp = entry["timestamp"]
            phase = entry["phase"]
            anchor_likely = entry["summary"]["anchor_likely"]
            anchor_uncertain = entry["summary"]["anchor_uncertain"]

            print(f"{timestamp[:19]} | {phase:<20} | "
                  f"LIKELY: {anchor_likely:>3} | UNCERTAIN: {anchor_uncertain:>3}")

            if "impact_vs_baseline" in entry:
                impact = entry["impact_vs_baseline"]
                print(f"                    | Impact: +{impact['likely_increase']} LIKELY upgrades")

        print("=" * 60)

    except Exception as e:
        print(f"ERROR: Could not display progress: {e}")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Track deployment metrics")
    parser.add_argument("action", choices=["baseline", "wave1", "wave2", "wave3", "progress"],
                       help="Action to perform")
    args = parser.parse_args()

    if args.action == "baseline":
        capture_baseline()
    elif args.action == "wave1":
        capture_wave_completion("Wave 1", 25)
    elif args.action == "wave2":
        capture_wave_completion("Wave 2", 50)
    elif args.action == "wave3":
        capture_wave_completion("Wave 3", 100)
    elif args.action == "progress":
        display_deployment_progress()