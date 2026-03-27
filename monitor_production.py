#!/usr/bin/env python3
"""
Production monitoring script for Parts Agent batch processing.

Provides real-time status updates and performance tracking for production scaling.
"""

import time
import subprocess
import sys
from pathlib import Path
from datetime import datetime

def run_count_results():
    """Run count_results.py and return output."""
    try:
        result = subprocess.run(
            [sys.executable, "src/count_results.py"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent
        )
        return result.stdout if result.returncode == 0 else f"Error: {result.stderr}"
    except Exception as e:
        return f"Error running count_results.py: {e}"

def get_processing_rates():
    """Calculate approximate processing rates from recent logs."""
    rates = {}
    output_dir = Path(__file__).parent / "output"

    for sheet in ["gmb", "dorman", "anchor", "smp", "four_seasons"]:
        log_file = output_dir / f"run_{sheet}_prod.txt"
        if log_file.exists():
            try:
                with open(log_file, 'r') as f:
                    lines = f.readlines()

                # Look for recent processing entries (last 100 lines)
                recent_lines = lines[-100:] if len(lines) > 100 else lines
                processing_count = sum(1 for line in recent_lines if "Processing row" in line)

                if processing_count > 0:
                    # Estimate rate based on file modification time and processing count
                    file_age_hours = (time.time() - log_file.stat().st_mtime) / 3600
                    if file_age_hours > 0:
                        rates[sheet] = processing_count / file_age_hours

            except Exception as e:
                rates[sheet] = f"Error: {e}"
        else:
            rates[sheet] = "Not started"

    return rates

def monitor_production(interval_minutes=30):
    """Main monitoring loop."""
    print("=== Parts Agent Production Monitor ===")
    print(f"Monitoring every {interval_minutes} minutes")
    print(f"Started: {datetime.now()}")
    print("=" * 50)

    iteration = 0

    while True:
        try:
            iteration += 1
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            print(f"\n[{timestamp}] --- Monitor Check #{iteration} ---")

            # Get processing status
            status_output = run_count_results()
            print("\nProcessing Status:")
            print(status_output)

            # Get processing rates
            rates = get_processing_rates()
            print("\nProcessing Rates (rows/hour):")
            for sheet, rate in rates.items():
                if isinstance(rate, (int, float)):
                    print(f"  {sheet:15}: {rate:6.1f} rows/hour")
                else:
                    print(f"  {sheet:15}: {rate}")

            # Check for error patterns in recent logs
            print("\nActive Processing Jobs:")
            output_dir = Path(__file__).parent / "output"
            for log_file in output_dir.glob("run_*_prod.txt"):
                if log_file.stat().st_mtime > time.time() - 7200:  # Modified in last 2 hours
                    size_kb = log_file.stat().st_size / 1024
                    print(f"  {log_file.name:25}: {size_kb:6.1f} KB (active)")

            print(f"\n[{timestamp}] Sleeping for {interval_minutes} minutes...")
            print("=" * 50)

            time.sleep(interval_minutes * 60)

        except KeyboardInterrupt:
            print(f"\n[{datetime.now()}] Monitor stopped by user")
            break
        except Exception as e:
            print(f"\n[{datetime.now()}] Monitor error: {e}")
            print("Continuing monitoring...")
            time.sleep(60)  # Wait 1 minute on error

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Monitor Parts Agent production processing")
    parser.add_argument("--interval", type=int, default=30,
                       help="Monitoring interval in minutes (default: 30)")
    parser.add_argument("--once", action="store_true",
                       help="Run once and exit (no loop)")

    args = parser.parse_args()

    if args.once:
        # Run once for immediate status check
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] Parts Agent Status Check")
        print("=" * 50)

        status_output = run_count_results()
        print(status_output)

        rates = get_processing_rates()
        print("\nProcessing Rates:")
        for sheet, rate in rates.items():
            if isinstance(rate, (int, float)):
                print(f"  {sheet}: {rate:.1f} rows/hour")
            else:
                print(f"  {sheet}: {rate}")
    else:
        monitor_production(args.interval)