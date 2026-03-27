"""
Priority Scheduler
Intelligent Processing Optimization (Priority 3)

Smart prioritization system that optimizes processing order based on:
- Historical success rates by brand and part type
- Part complexity indicators (description length, OEM count)
- System load and resource availability
- Processing time estimates
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import sys

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from analytics.stats_engine import StatsEngine
from analytics.performance_metrics import PerformanceTracker

class PriorityScheduler:
    """Smart processing scheduler with adaptive prioritization."""

    def __init__(self, excel_path: str = None):
        """Initialize the priority scheduler."""
        if excel_path is None:
            excel_path = str(Path(__file__).parent.parent.parent / "FISHER SKP INTERCHANGE 20260302.xlsx")

        self.excel_path = excel_path
        self.stats_engine = StatsEngine(excel_path)
        self.performance_tracker = PerformanceTracker()

        # Historical data cache
        self.brand_success_rates = {}
        self.part_type_complexity = {}
        self.processing_history = []

        # Priority weights (can be tuned)
        self.weights = {
            'success_probability': 0.30,  # Higher success rate = higher priority
            'complexity_score': 0.20,     # Lower complexity = higher priority
            'resource_efficiency': 0.20,  # Better resource usage = higher priority
            'business_value': 0.15,       # Higher sales volume = higher priority
            'processing_speed': 0.15       # Faster estimated processing = higher priority
        }

        # Load historical data
        self._load_historical_data()

    def _load_historical_data(self):
        """Load and analyze historical processing data."""
        try:
            # Get comprehensive statistics
            stats = self.stats_engine.get_summary_stats()

            # Extract brand success rates from sheet breakdown
            if 'by_sheet' in stats:
                for brand, brand_stats in stats['by_sheet'].items():
                    total_processed = brand_stats.get('processed', 0)
                    yes_count = brand_stats.get('YES', 0)
                    likely_count = brand_stats.get('LIKELY', 0)

                    if total_processed > 0:
                        success_rate = (yes_count + likely_count) / total_processed
                        self.brand_success_rates[brand] = {
                            'success_rate': success_rate,
                            'total_processed': total_processed,
                            'confidence': min(total_processed / 100.0, 1.0)  # More data = higher confidence
                        }

            # Analyze part type complexity (placeholder - would need historical timing data)
            self.part_type_complexity = {
                'ENGINE MOUNT': {'complexity': 0.3, 'avg_time': 12.0},
                'BRAKE PAD': {'complexity': 0.2, 'avg_time': 8.0},
                'FILTER': {'complexity': 0.1, 'avg_time': 5.0},
                'SENSOR': {'complexity': 0.4, 'avg_time': 15.0},
                'BELT': {'complexity': 0.2, 'avg_time': 7.0},
                'DEFAULT': {'complexity': 0.25, 'avg_time': 10.0}
            }

        except Exception as e:
            print(f"Warning: Could not load historical data: {e}")
            # Use default values
            self.brand_success_rates = {
                'ANCHOR': {'success_rate': 0.75, 'total_processed': 100, 'confidence': 1.0},
                'DORMAN': {'success_rate': 0.65, 'total_processed': 50, 'confidence': 0.5},
                'GMB': {'success_rate': 0.80, 'total_processed': 5, 'confidence': 0.05}
            }

    def calculate_priority_score(self, row_data: Dict) -> float:
        """Calculate priority score for a processing row."""
        try:
            brand = row_data.get('current_supplier', 'UNKNOWN')
            part_type = row_data.get('part_type', 'DEFAULT')
            part_number = row_data.get('part_number', '')
            sales_quantity = row_data.get('call12', 0)

            # 1. Success Probability Score (0-1)
            brand_data = self.brand_success_rates.get(brand, {'success_rate': 0.5, 'confidence': 0.1})
            success_score = brand_data['success_rate'] * brand_data['confidence']

            # 2. Complexity Score (0-1, lower complexity = higher score)
            part_complexity_data = self.part_type_complexity.get(part_type, self.part_type_complexity['DEFAULT'])
            complexity_score = 1.0 - part_complexity_data['complexity']

            # 3. Resource Efficiency Score (0-1)
            current_load = self.performance_tracker.get_real_time_metrics()
            system_metrics = current_load.get('system', {})
            cpu_load = system_metrics.get('cpu_percent', 50) / 100.0
            memory_load = system_metrics.get('memory_percent', 50) / 100.0

            # Lower system load = higher efficiency score
            efficiency_score = 1.0 - (cpu_load * 0.6 + memory_load * 0.4)

            # 4. Business Value Score (0-1)
            max_sales = 100  # Normalize based on typical sales volume
            business_score = min(sales_quantity / max_sales, 1.0) if sales_quantity else 0.1

            # 5. Processing Speed Score (0-1)
            estimated_time = part_complexity_data['avg_time']
            max_time = 20.0  # Normalize based on maximum typical processing time
            speed_score = 1.0 - (estimated_time / max_time)

            # Calculate weighted total score
            total_score = (
                success_score * self.weights['success_probability'] +
                complexity_score * self.weights['complexity_score'] +
                efficiency_score * self.weights['resource_efficiency'] +
                business_score * self.weights['business_value'] +
                speed_score * self.weights['processing_speed']
            )

            return max(0.0, min(1.0, total_score))  # Clamp to [0, 1]

        except Exception as e:
            print(f"Warning: Error calculating priority score: {e}")
            return 0.5  # Default medium priority

    def prioritize_batch(self, rows: List[Dict], batch_size: int = 50) -> List[Dict]:
        """Prioritize a batch of rows for processing."""
        try:
            # Calculate priority scores
            scored_rows = []
            for i, row in enumerate(rows):
                score = self.calculate_priority_score(row)
                scored_rows.append({
                    'index': i,
                    'row': row,
                    'priority_score': score,
                    'estimated_time': self._estimate_processing_time(row)
                })

            # Sort by priority score (descending)
            scored_rows.sort(key=lambda x: x['priority_score'], reverse=True)

            # Select top batch_size rows
            prioritized_batch = scored_rows[:batch_size]

            # Log prioritization results
            self._log_prioritization(prioritized_batch)

            return [item['row'] for item in prioritized_batch]

        except Exception as e:
            print(f"Error prioritizing batch: {e}")
            return rows[:batch_size]  # Fallback to simple slicing

    def _estimate_processing_time(self, row_data: Dict) -> float:
        """Estimate processing time for a row."""
        part_type = row_data.get('part_type', 'DEFAULT')
        complexity_data = self.part_type_complexity.get(part_type, self.part_type_complexity['DEFAULT'])

        base_time = complexity_data['avg_time']

        # Adjust based on current system load
        current_load = self.performance_tracker.get_real_time_metrics()
        system_metrics = current_load.get('system', {})
        load_factor = 1.0 + (system_metrics.get('cpu_percent', 50) / 100.0) * 0.5

        return base_time * load_factor

    def _log_prioritization(self, prioritized_batch: List[Dict]):
        """Log prioritization decisions."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Calculate summary statistics
        scores = [item['priority_score'] for item in prioritized_batch]
        avg_score = sum(scores) / len(scores) if scores else 0
        min_score = min(scores) if scores else 0
        max_score = max(scores) if scores else 0

        print(f"\n[PRIORITY] {timestamp} - Batch prioritized:")
        print(f"   Rows prioritized: {len(prioritized_batch)}")
        print(f"   Score range: {min_score:.3f} - {max_score:.3f}")
        print(f"   Average score: {avg_score:.3f}")

        # Show top 5 prioritized items
        print(f"   Top 5 priorities:")
        for i, item in enumerate(prioritized_batch[:5]):
            row = item['row']
            brand = row.get('current_supplier', 'Unknown')
            part_type = row.get('part_type', 'Unknown')
            part_num = row.get('part_number', 'Unknown')
            score = item['priority_score']
            print(f"     {i+1}. {brand} {part_num} ({part_type}) - Score: {score:.3f}")

    def get_optimal_batch_size(self) -> int:
        """Determine optimal batch size based on current system resources."""
        try:
            metrics = self.performance_tracker.get_real_time_metrics()

            # Base batch size
            base_size = 50

            # Adjust based on available resources
            system_metrics = metrics.get('system', {})
            cpu_usage = system_metrics.get('cpu_percent', 50)
            memory_usage = system_metrics.get('memory_percent', 50)

            # Reduce batch size if system is under load
            if cpu_usage > 80 or memory_usage > 80:
                size_factor = 0.5  # Reduce to 50%
            elif cpu_usage > 60 or memory_usage > 60:
                size_factor = 0.75  # Reduce to 75%
            else:
                size_factor = 1.0  # Full batch size

            optimal_size = max(10, int(base_size * size_factor))

            print(f"[OPTIMIZATION] Optimal batch size: {optimal_size} (CPU: {cpu_usage}%, Memory: {memory_usage}%)")

            return optimal_size

        except Exception as e:
            print(f"Warning: Could not determine optimal batch size: {e}")
            return 50  # Default fallback

    def update_success_rate(self, brand: str, part_type: str, success: bool):
        """Update success rates based on processing results."""
        try:
            # Update brand success rate
            if brand not in self.brand_success_rates:
                self.brand_success_rates[brand] = {
                    'success_rate': 0.5,
                    'total_processed': 0,
                    'confidence': 0.0
                }

            brand_data = self.brand_success_rates[brand]
            total = brand_data['total_processed']
            current_successes = brand_data['success_rate'] * total

            # Update with new result
            new_successes = current_successes + (1 if success else 0)
            new_total = total + 1
            new_success_rate = new_successes / new_total

            brand_data['success_rate'] = new_success_rate
            brand_data['total_processed'] = new_total
            brand_data['confidence'] = min(new_total / 100.0, 1.0)

            print(f"[UPDATE] {brand} success rate updated: {new_success_rate:.3f} ({new_total} total)")

        except Exception as e:
            print(f"Warning: Could not update success rate: {e}")

    def get_optimization_report(self) -> Dict:
        """Generate optimization performance report."""
        try:
            current_metrics = self.performance_tracker.get_real_time_metrics()

            report = {
                'timestamp': datetime.now().isoformat(),
                'brand_success_rates': self.brand_success_rates,
                'part_type_complexity': self.part_type_complexity,
                'current_system_load': {
                    'cpu_percent': current_metrics.get('system', {}).get('cpu_percent', 0),
                    'memory_percent': current_metrics.get('system', {}).get('memory_percent', 0),
                    'chrome_processes': current_metrics.get('chrome_processes', 0)
                },
                'optimization_weights': self.weights,
                'recommended_batch_size': self.get_optimal_batch_size(),
                'total_brands_tracked': len(self.brand_success_rates),
                'total_part_types_tracked': len(self.part_type_complexity)
            }

            return report

        except Exception as e:
            print(f"Error generating optimization report: {e}")
            return {'error': str(e)}

if __name__ == "__main__":
    # Test the priority scheduler
    print("Testing Priority Scheduler...")

    scheduler = PriorityScheduler()

    # Test data
    test_rows = [
        {'current_supplier': 'ANCHOR', 'part_type': 'ENGINE MOUNT', 'part_number': '3217', 'call12': 50},
        {'current_supplier': 'DORMAN', 'part_type': 'BRAKE PAD', 'part_number': '1234', 'call12': 25},
        {'current_supplier': 'GMB', 'part_type': 'FILTER', 'part_number': '5678', 'call12': 75},
    ]

    # Test prioritization
    prioritized = scheduler.prioritize_batch(test_rows, batch_size=3)

    # Test optimization report
    report = scheduler.get_optimization_report()
    print(f"\nOptimization Report Generated: {len(report)} sections")

    print("Priority Scheduler test completed.")