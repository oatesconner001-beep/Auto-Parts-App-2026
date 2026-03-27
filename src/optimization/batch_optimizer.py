"""
Batch Optimizer
Intelligent Processing Optimization (Priority 3)

Optimizes batch processing operations by:
- Determining optimal batch sizes based on system resources
- Balancing processing speed with quality
- Managing parallel processing workflows
- Adaptive retry strategies and error handling
"""

import time
import threading
import queue
import concurrent.futures
from datetime import datetime, timedelta
from typing import List, Dict, Callable, Optional, Tuple
from pathlib import Path
import sys

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from analytics.performance_metrics import PerformanceTracker
from optimization.priority_scheduler import PriorityScheduler

class BatchOptimizer:
    """Intelligent batch processing optimizer."""

    def __init__(self, excel_path: str = None):
        """Initialize the batch optimizer."""
        self.performance_tracker = PerformanceTracker()
        self.priority_scheduler = PriorityScheduler(excel_path)

        # Optimization parameters
        self.config = {
            'min_batch_size': 5,
            'max_batch_size': 100,
            'target_cpu_usage': 70.0,  # Target CPU usage percentage
            'target_memory_usage': 75.0,  # Target memory usage percentage
            'max_parallel_workers': 4,
            'retry_attempts': 3,
            'retry_delay_base': 2.0,  # Base delay in seconds
            'quality_threshold': 0.8,  # Minimum quality score to accept results
            'performance_window': 300,  # Performance tracking window (seconds)
        }

        # Runtime statistics
        self.stats = {
            'total_processed': 0,
            'total_successful': 0,
            'total_failed': 0,
            'total_retries': 0,
            'total_processing_time': 0.0,
            'average_processing_time': 0.0,
            'current_throughput': 0.0,  # Items per minute
            'optimization_adjustments': 0,
            'start_time': datetime.now()
        }

        # Performance history
        self.performance_history = []
        self.batch_history = []

        print("[BATCH_OPTIMIZER] Initialized with intelligent processing optimization")

    def optimize_batch_processing(self,
                                 data_rows: List[Dict],
                                 processing_function: Callable,
                                 progress_callback: Optional[Callable] = None) -> Dict:
        """Optimize batch processing with adaptive strategies."""

        start_time = datetime.now()
        total_rows = len(data_rows)

        print(f"[BATCH_OPTIMIZER] Starting optimized processing of {total_rows} rows")

        try:
            # Step 1: Analyze and prioritize rows
            prioritized_rows = self.priority_scheduler.prioritize_batch(data_rows, len(data_rows))

            # Step 2: Determine optimal batch configuration
            batch_config = self._calculate_optimal_batch_config()
            batch_size = batch_config['batch_size']
            parallel_workers = batch_config['parallel_workers']

            print(f"[BATCH_OPTIMIZER] Using batch size: {batch_size}, workers: {parallel_workers}")

            # Step 3: Process in optimized batches
            results = []
            processed_count = 0

            for i in range(0, len(prioritized_rows), batch_size):
                batch = prioritized_rows[i:i + batch_size]
                batch_start = datetime.now()

                # Process batch with parallel workers
                batch_results = self._process_batch_parallel(
                    batch, processing_function, parallel_workers
                )

                results.extend(batch_results)
                processed_count += len(batch)

                # Update statistics and performance tracking
                batch_duration = (datetime.now() - batch_start).total_seconds()
                self._update_batch_statistics(len(batch), batch_duration, batch_results)

                # Progress callback
                if progress_callback:
                    progress_callback(processed_count, total_rows)

                # Adaptive optimization: adjust parameters based on performance
                if processed_count % (batch_size * 2) == 0:  # Every 2 batches
                    self._adaptive_optimization_adjustment()
                    batch_config = self._calculate_optimal_batch_config()
                    batch_size = batch_config['batch_size']
                    parallel_workers = batch_config['parallel_workers']

                print(f"[BATCH_OPTIMIZER] Processed batch {i//batch_size + 1}: "
                      f"{len(batch)} rows in {batch_duration:.2f}s")

            # Final statistics
            total_duration = (datetime.now() - start_time).total_seconds()
            self._finalize_processing_statistics(total_duration, results)

            return {
                'success': True,
                'total_processed': processed_count,
                'total_duration': total_duration,
                'results': results,
                'statistics': self.stats.copy(),
                'optimization_report': self._generate_optimization_report()
            }

        except Exception as e:
            print(f"[BATCH_OPTIMIZER] Error during batch processing: {e}")
            return {
                'success': False,
                'error': str(e),
                'total_processed': processed_count if 'processed_count' in locals() else 0,
                'results': results if 'results' in locals() else []
            }

    def _calculate_optimal_batch_config(self) -> Dict:
        """Calculate optimal batch size and worker count based on current system state."""
        try:
            # Get current system metrics
            metrics = self.performance_tracker.get_real_time_metrics()
            system_metrics = metrics.get('system', {})
            cpu_usage = system_metrics.get('cpu_percent', 50)
            memory_usage = system_metrics.get('memory_percent', 50)

            # Base configuration
            base_batch_size = 25
            base_workers = 2

            # Adjust based on resource availability
            cpu_factor = self._calculate_resource_factor(cpu_usage, self.config['target_cpu_usage'])
            memory_factor = self._calculate_resource_factor(memory_usage, self.config['target_memory_usage'])

            # Use the more restrictive factor
            resource_factor = min(cpu_factor, memory_factor)

            # Calculate optimal batch size
            optimal_batch_size = int(base_batch_size * resource_factor)
            optimal_batch_size = max(self.config['min_batch_size'],
                                   min(optimal_batch_size, self.config['max_batch_size']))

            # Calculate optimal worker count
            optimal_workers = int(base_workers * resource_factor)
            optimal_workers = max(1, min(optimal_workers, self.config['max_parallel_workers']))

            # Consider recent performance history
            if self.batch_history:
                recent_performance = self._analyze_recent_performance()
                if recent_performance['efficiency'] < 0.7:  # Poor efficiency
                    optimal_batch_size = max(self.config['min_batch_size'], optimal_batch_size // 2)
                    optimal_workers = max(1, optimal_workers - 1)

            return {
                'batch_size': optimal_batch_size,
                'parallel_workers': optimal_workers,
                'resource_factor': resource_factor,
                'cpu_usage': cpu_usage,
                'memory_usage': memory_usage
            }

        except Exception as e:
            print(f"Warning: Could not calculate optimal batch config: {e}")
            return {
                'batch_size': 25,
                'parallel_workers': 2,
                'resource_factor': 1.0,
                'cpu_usage': 50,
                'memory_usage': 50
            }

    def _calculate_resource_factor(self, current_usage: float, target_usage: float) -> float:
        """Calculate resource utilization factor for optimization."""
        if current_usage < target_usage * 0.5:
            return 1.5  # Increase load if under-utilized
        elif current_usage < target_usage:
            return 1.0  # Optimal range
        elif current_usage < target_usage * 1.2:
            return 0.8  # Slight reduction
        else:
            return 0.5  # Significant reduction for overload

    def _process_batch_parallel(self,
                               batch: List[Dict],
                               processing_function: Callable,
                               max_workers: int) -> List[Dict]:
        """Process a batch using parallel workers with error handling."""
        results = []

        def process_single_item(item_data):
            """Process a single item with retry logic."""
            for attempt in range(self.config['retry_attempts']):
                try:
                    result = processing_function(item_data)
                    if self._validate_result_quality(result):
                        return {'success': True, 'data': result, 'attempts': attempt + 1}
                    else:
                        print(f"[BATCH_OPTIMIZER] Quality check failed for item, attempt {attempt + 1}")
                        if attempt < self.config['retry_attempts'] - 1:
                            time.sleep(self.config['retry_delay_base'] * (attempt + 1))

                except Exception as e:
                    self.stats['total_failed'] += 1
                    print(f"[BATCH_OPTIMIZER] Processing error (attempt {attempt + 1}): {e}")
                    if attempt < self.config['retry_attempts'] - 1:
                        time.sleep(self.config['retry_delay_base'] * (attempt + 1))
                        self.stats['total_retries'] += 1

            return {'success': False, 'error': 'Max retries exceeded', 'attempts': self.config['retry_attempts']}

        # Process batch using thread pool
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_item = {executor.submit(process_single_item, item): item for item in batch}

            for future in concurrent.futures.as_completed(future_to_item):
                item = future_to_item[future]
                try:
                    result = future.result()
                    results.append({
                        'item': item,
                        'result': result,
                        'timestamp': datetime.now().isoformat()
                    })

                    if result['success']:
                        self.stats['total_successful'] += 1
                    else:
                        self.stats['total_failed'] += 1

                except Exception as e:
                    print(f"[BATCH_OPTIMIZER] Thread execution error: {e}")
                    results.append({
                        'item': item,
                        'result': {'success': False, 'error': str(e)},
                        'timestamp': datetime.now().isoformat()
                    })
                    self.stats['total_failed'] += 1

        return results

    def _validate_result_quality(self, result: Dict) -> bool:
        """Validate the quality of processing results."""
        try:
            # Check for required fields
            if not isinstance(result, dict):
                return False

            # Check for error indicators
            if result.get('error'):
                return False

            # Check confidence score if available
            confidence = result.get('confidence', 1.0)
            if isinstance(confidence, (int, float)) and confidence < self.config['quality_threshold']:
                return False

            # Check match result validity
            match_result = result.get('match_result', '')
            valid_results = {'YES', 'LIKELY', 'UNCERTAIN', 'NO'}
            if match_result not in valid_results:
                return False

            return True

        except Exception as e:
            print(f"Warning: Quality validation error: {e}")
            return True  # Default to accepting if validation fails

    def _update_batch_statistics(self, batch_size: int, duration: float, results: List[Dict]):
        """Update performance statistics after batch completion."""
        self.stats['total_processed'] += batch_size
        self.stats['total_processing_time'] += duration

        # Calculate averages
        if self.stats['total_processed'] > 0:
            self.stats['average_processing_time'] = (
                self.stats['total_processing_time'] / self.stats['total_processed']
            )

            # Calculate throughput (items per minute)
            total_minutes = (datetime.now() - self.stats['start_time']).total_seconds() / 60.0
            if total_minutes > 0:
                self.stats['current_throughput'] = self.stats['total_processed'] / total_minutes

        # Record batch performance
        batch_record = {
            'timestamp': datetime.now().isoformat(),
            'batch_size': batch_size,
            'duration': duration,
            'throughput': batch_size / duration if duration > 0 else 0,
            'success_rate': sum(1 for r in results if r.get('result', {}).get('success', False)) / len(results),
            'system_metrics': self.performance_tracker.get_real_time_metrics()
        }

        self.batch_history.append(batch_record)

        # Keep only recent history (last 50 batches)
        if len(self.batch_history) > 50:
            self.batch_history = self.batch_history[-50:]

    def _analyze_recent_performance(self) -> Dict:
        """Analyze recent processing performance for optimization."""
        if not self.batch_history:
            return {'efficiency': 1.0, 'trend': 'stable'}

        recent_batches = self.batch_history[-10:]  # Last 10 batches

        # Calculate average efficiency metrics
        avg_throughput = sum(b['throughput'] for b in recent_batches) / len(recent_batches)
        avg_success_rate = sum(b['success_rate'] for b in recent_batches) / len(recent_batches)

        # Efficiency score combines throughput and success rate
        efficiency = (avg_throughput / 10.0) * avg_success_rate  # Normalized throughput * success rate
        efficiency = min(1.0, efficiency)  # Cap at 1.0

        # Determine trend
        if len(recent_batches) >= 5:
            early_batches = recent_batches[:5]
            late_batches = recent_batches[-5:]

            early_avg = sum(b['throughput'] for b in early_batches) / len(early_batches)
            late_avg = sum(b['throughput'] for b in late_batches) / len(late_batches)

            if late_avg > early_avg * 1.1:
                trend = 'improving'
            elif late_avg < early_avg * 0.9:
                trend = 'declining'
            else:
                trend = 'stable'
        else:
            trend = 'insufficient_data'

        return {
            'efficiency': efficiency,
            'avg_throughput': avg_throughput,
            'avg_success_rate': avg_success_rate,
            'trend': trend,
            'sample_size': len(recent_batches)
        }

    def _adaptive_optimization_adjustment(self):
        """Make adaptive adjustments based on performance analysis."""
        performance = self._analyze_recent_performance()

        if performance['efficiency'] < 0.6:  # Poor performance
            print(f"[BATCH_OPTIMIZER] Performance below threshold ({performance['efficiency']:.2f}), adjusting parameters")

            # Reduce load
            self.config['target_cpu_usage'] = max(50.0, self.config['target_cpu_usage'] - 5.0)
            self.config['max_parallel_workers'] = max(1, self.config['max_parallel_workers'] - 1)

            self.stats['optimization_adjustments'] += 1

        elif performance['efficiency'] > 0.9 and performance['trend'] == 'stable':
            print(f"[BATCH_OPTIMIZER] High performance detected ({performance['efficiency']:.2f}), optimizing for higher throughput")

            # Increase load cautiously
            self.config['target_cpu_usage'] = min(85.0, self.config['target_cpu_usage'] + 2.0)
            self.config['max_parallel_workers'] = min(6, self.config['max_parallel_workers'] + 1)

            self.stats['optimization_adjustments'] += 1

    def _finalize_processing_statistics(self, total_duration: float, results: List[Dict]):
        """Finalize processing statistics and generate summary."""
        self.stats['total_processing_time'] = total_duration

        # Calculate final success rate
        successful_results = sum(1 for r in results if r.get('result', {}).get('success', False))
        self.stats['final_success_rate'] = successful_results / len(results) if results else 0.0

        # Calculate final throughput
        self.stats['final_throughput'] = len(results) / total_duration if total_duration > 0 else 0.0

        print(f"\n[BATCH_OPTIMIZER] Processing Complete:")
        print(f"   Total processed: {self.stats['total_processed']}")
        print(f"   Successful: {self.stats['total_successful']}")
        print(f"   Failed: {self.stats['total_failed']}")
        print(f"   Total duration: {total_duration:.2f}s")
        print(f"   Final throughput: {self.stats['final_throughput']:.2f} items/second")
        print(f"   Success rate: {self.stats['final_success_rate']:.1%}")
        print(f"   Optimization adjustments: {self.stats['optimization_adjustments']}")

    def _generate_optimization_report(self) -> Dict:
        """Generate comprehensive optimization performance report."""
        recent_performance = self._analyze_recent_performance()
        current_config = self._calculate_optimal_batch_config()

        return {
            'processing_statistics': self.stats.copy(),
            'recent_performance': recent_performance,
            'current_configuration': {
                'batch_size_range': f"{self.config['min_batch_size']}-{self.config['max_batch_size']}",
                'target_cpu_usage': self.config['target_cpu_usage'],
                'target_memory_usage': self.config['target_memory_usage'],
                'max_parallel_workers': self.config['max_parallel_workers'],
                'current_optimal_config': current_config
            },
            'optimization_insights': {
                'efficiency_score': recent_performance.get('efficiency', 0.0),
                'performance_trend': recent_performance.get('trend', 'unknown'),
                'total_adjustments': self.stats['optimization_adjustments'],
                'recommendations': self._generate_optimization_recommendations()
            },
            'batch_history_summary': {
                'total_batches': len(self.batch_history),
                'avg_batch_duration': sum(b['duration'] for b in self.batch_history) / len(self.batch_history) if self.batch_history else 0,
                'avg_batch_throughput': sum(b['throughput'] for b in self.batch_history) / len(self.batch_history) if self.batch_history else 0
            },
            'timestamp': datetime.now().isoformat()
        }

    def _generate_optimization_recommendations(self) -> List[str]:
        """Generate optimization recommendations based on performance analysis."""
        recommendations = []
        performance = self._analyze_recent_performance()

        if performance['efficiency'] < 0.7:
            recommendations.append("Consider reducing batch sizes to improve processing stability")
            recommendations.append("Monitor system resource usage and reduce parallel workers if necessary")

        if performance['avg_success_rate'] < 0.8:
            recommendations.append("Increase retry attempts or improve error handling")
            recommendations.append("Review quality validation criteria")

        if performance['trend'] == 'declining':
            recommendations.append("System performance is declining - consider resource optimization")
            recommendations.append("Review recent system changes or background processes")

        if self.stats['optimization_adjustments'] > 10:
            recommendations.append("Frequent optimization adjustments detected - consider manual tuning")

        if not recommendations:
            recommendations.append("System is performing well - continue current optimization strategy")

        return recommendations

if __name__ == "__main__":
    # Test the batch optimizer
    print("Testing Batch Optimizer...")

    optimizer = BatchOptimizer()

    # Mock processing function
    def mock_processing_function(row_data):
        import random
        time.sleep(random.uniform(0.1, 0.5))  # Simulate processing time

        return {
            'match_result': random.choice(['YES', 'LIKELY', 'UNCERTAIN', 'NO']),
            'confidence': random.uniform(0.6, 1.0),
            'processing_time': random.uniform(0.1, 0.5)
        }

    # Test data
    test_data = [
        {'current_supplier': 'ANCHOR', 'part_type': 'ENGINE MOUNT', 'part_number': f'test{i}'}
        for i in range(10)
    ]

    # Test optimization
    result = optimizer.optimize_batch_processing(test_data, mock_processing_function)

    print(f"\nOptimization test completed:")
    print(f"   Success: {result['success']}")
    print(f"   Total processed: {result['total_processed']}")
    print(f"   Duration: {result['total_duration']:.2f}s")

    if result['success']:
        report = result['optimization_report']
        print(f"   Efficiency: {report['optimization_insights']['efficiency_score']:.2f}")
        print(f"   Recommendations: {len(report['optimization_insights']['recommendations'])}")

    print("Batch Optimizer test completed.")