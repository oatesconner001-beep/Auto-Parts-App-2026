"""
Anomaly Detector
Data Quality & Validation Layer (Priority 4)

Detects anomalies and unusual patterns in:
- Processing results and confidence scores
- Batch processing patterns
- Performance degradation
- Data quality drift
- System behavior changes
"""

import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict, deque
import statistics
import sys

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

class AnomalyDetector:
    """Advanced anomaly detection system for Parts Agent processing."""

    def __init__(self, excel_path: str = None):
        """Initialize the anomaly detector."""
        if excel_path is None:
            excel_path = str(Path(__file__).parent.parent.parent / "FISHER SKP INTERCHANGE 20260302.xlsx")

        self.excel_path = excel_path

        # Statistical thresholds for anomaly detection
        self.thresholds = {
            'confidence_std_dev': 25.0,  # Max std deviation for confidence scores
            'processing_time_factor': 3.0,  # Max factor above baseline processing time
            'success_rate_drop': 0.2,  # Max drop in success rate (20%)
            'batch_size_deviation': 0.5,  # Max deviation from normal batch size
            'quality_score_drop': 0.3,  # Max drop in quality score
            'error_rate_spike': 0.1,  # Max acceptable error rate spike
        }

        # Historical data for baseline calculations
        self.baseline_data = {
            'confidence_scores': deque(maxlen=1000),
            'processing_times': deque(maxlen=1000),
            'success_rates': deque(maxlen=100),  # Per-batch success rates
            'batch_sizes': deque(maxlen=100),
            'quality_scores': deque(maxlen=1000),
            'error_counts': deque(maxlen=100)
        }

        # Current session tracking
        self.session_data = {
            'start_time': datetime.now(),
            'anomalies_detected': [],
            'warnings_issued': 0,
            'critical_alerts': 0
        }

        # Anomaly patterns
        self.anomaly_patterns = {
            'confidence_anomalies': {
                'sudden_confidence_drop': 'Sudden drop in confidence scores detected',
                'confidence_variance_spike': 'Unusual variance in confidence scores',
                'confidence_calibration_drift': 'Confidence calibration appears to be drifting'
            },
            'performance_anomalies': {
                'processing_slowdown': 'Processing speed significantly slower than baseline',
                'batch_size_anomaly': 'Unusual batch size detected',
                'memory_spike': 'Memory usage spike detected'
            },
            'quality_anomalies': {
                'quality_degradation': 'Result quality degradation detected',
                'reasoning_quality_drop': 'Reasoning quality below expected levels',
                'consistency_violation': 'Result consistency violation detected'
            },
            'system_anomalies': {
                'error_rate_spike': 'Error rate above normal threshold',
                'success_rate_drop': 'Success rate dropped significantly',
                'pattern_change': 'Processing pattern change detected'
            }
        }

        print("[ANOMALY_DETECTOR] Initialized with advanced pattern detection")

    def record_processing_result(self, result_data: Dict, processing_time: float = None,
                                batch_context: Optional[Dict] = None):
        """Record a processing result for anomaly analysis."""
        try:
            # Record confidence score
            confidence = result_data.get('confidence')
            if confidence is not None:
                try:
                    self.baseline_data['confidence_scores'].append(int(confidence))
                except (ValueError, TypeError):
                    pass

            # Record processing time
            if processing_time is not None:
                self.baseline_data['processing_times'].append(processing_time)

            # Record quality score if available
            quality_score = result_data.get('quality_score')
            if quality_score is not None:
                self.baseline_data['quality_scores'].append(float(quality_score))

            # Record batch-level data
            if batch_context:
                success = result_data.get('match_result') in ['YES', 'LIKELY']
                batch_context.setdefault('successes', 0)
                batch_context.setdefault('total', 0)

                batch_context['successes'] += int(success)
                batch_context['total'] += 1

        except Exception as e:
            print(f"Warning: Error recording processing result: {e}")

    def record_batch_completion(self, batch_stats: Dict):
        """Record batch completion for anomaly analysis."""
        try:
            # Record batch success rate
            total = batch_stats.get('total', 0)
            successes = batch_stats.get('successes', 0)
            if total > 0:
                success_rate = successes / total
                self.baseline_data['success_rates'].append(success_rate)

            # Record batch size
            batch_size = batch_stats.get('batch_size', 0)
            if batch_size > 0:
                self.baseline_data['batch_sizes'].append(batch_size)

            # Record error count
            errors = batch_stats.get('errors', 0)
            self.baseline_data['error_counts'].append(errors)

        except Exception as e:
            print(f"Warning: Error recording batch completion: {e}")

    def detect_anomalies(self) -> Dict:
        """Detect anomalies in current processing data."""
        anomaly_report = {
            'timestamp': datetime.now().isoformat(),
            'anomalies_detected': [],
            'severity_counts': {'critical': 0, 'warning': 0, 'info': 0},
            'analysis_results': {}
        }

        try:
            # Confidence anomaly detection
            confidence_anomalies = self._detect_confidence_anomalies()
            anomaly_report['analysis_results']['confidence'] = confidence_anomalies
            anomaly_report['anomalies_detected'].extend(confidence_anomalies.get('anomalies', []))

            # Performance anomaly detection
            performance_anomalies = self._detect_performance_anomalies()
            anomaly_report['analysis_results']['performance'] = performance_anomalies
            anomaly_report['anomalies_detected'].extend(performance_anomalies.get('anomalies', []))

            # Quality anomaly detection
            quality_anomalies = self._detect_quality_anomalies()
            anomaly_report['analysis_results']['quality'] = quality_anomalies
            anomaly_report['anomalies_detected'].extend(quality_anomalies.get('anomalies', []))

            # System pattern anomaly detection
            system_anomalies = self._detect_system_anomalies()
            anomaly_report['analysis_results']['system'] = system_anomalies
            anomaly_report['anomalies_detected'].extend(system_anomalies.get('anomalies', []))

            # Count anomalies by severity
            for anomaly in anomaly_report['anomalies_detected']:
                severity = anomaly.get('severity', 'info')
                anomaly_report['severity_counts'][severity] += 1

            # Store detected anomalies
            self.session_data['anomalies_detected'].extend(anomaly_report['anomalies_detected'])

        except Exception as e:
            anomaly_report['anomalies_detected'].append({
                'type': 'system_error',
                'severity': 'critical',
                'description': f"Error in anomaly detection: {str(e)}",
                'timestamp': datetime.now().isoformat()
            })

        return anomaly_report

    def _detect_confidence_anomalies(self) -> Dict:
        """Detect anomalies in confidence scores."""
        result = {'anomalies': [], 'statistics': {}}

        confidence_scores = list(self.baseline_data['confidence_scores'])
        if len(confidence_scores) < 10:
            return result

        try:
            # Calculate baseline statistics
            mean_confidence = statistics.mean(confidence_scores)
            std_confidence = statistics.stdev(confidence_scores) if len(confidence_scores) > 1 else 0
            recent_scores = confidence_scores[-20:]  # Last 20 scores

            result['statistics'] = {
                'mean_confidence': mean_confidence,
                'std_confidence': std_confidence,
                'recent_mean': statistics.mean(recent_scores),
                'total_samples': len(confidence_scores)
            }

            # Detect sudden confidence drop
            if len(recent_scores) >= 10:
                recent_mean = statistics.mean(recent_scores)
                if mean_confidence - recent_mean > 15:  # 15-point drop
                    result['anomalies'].append({
                        'type': 'sudden_confidence_drop',
                        'severity': 'warning',
                        'description': f"Recent confidence average ({recent_mean:.1f}) significantly below baseline ({mean_confidence:.1f})",
                        'timestamp': datetime.now().isoformat(),
                        'details': {'baseline': mean_confidence, 'recent': recent_mean}
                    })

            # Detect confidence variance spike
            if std_confidence > self.thresholds['confidence_std_dev']:
                result['anomalies'].append({
                    'type': 'confidence_variance_spike',
                    'severity': 'warning',
                    'description': f"High confidence variance detected (σ={std_confidence:.1f})",
                    'timestamp': datetime.now().isoformat(),
                    'details': {'std_dev': std_confidence, 'threshold': self.thresholds['confidence_std_dev']}
                })

            # Detect calibration drift (comparing first and last quartiles)
            if len(confidence_scores) >= 40:
                first_quartile = confidence_scores[:len(confidence_scores)//4]
                last_quartile = confidence_scores[-len(confidence_scores)//4:]

                first_mean = statistics.mean(first_quartile)
                last_mean = statistics.mean(last_quartile)

                if abs(first_mean - last_mean) > 10:
                    drift_direction = "upward" if last_mean > first_mean else "downward"
                    result['anomalies'].append({
                        'type': 'confidence_calibration_drift',
                        'severity': 'info',
                        'description': f"Confidence calibration {drift_direction} drift detected ({first_mean:.1f} → {last_mean:.1f})",
                        'timestamp': datetime.now().isoformat(),
                        'details': {'early_mean': first_mean, 'late_mean': last_mean}
                    })

        except Exception as e:
            result['anomalies'].append({
                'type': 'confidence_analysis_error',
                'severity': 'warning',
                'description': f"Error analyzing confidence: {str(e)}",
                'timestamp': datetime.now().isoformat()
            })

        return result

    def _detect_performance_anomalies(self) -> Dict:
        """Detect performance anomalies."""
        result = {'anomalies': [], 'statistics': {}}

        processing_times = list(self.baseline_data['processing_times'])
        batch_sizes = list(self.baseline_data['batch_sizes'])

        try:
            # Processing time anomalies
            if len(processing_times) >= 10:
                baseline_time = statistics.median(processing_times[:-10])  # Exclude recent samples
                recent_times = processing_times[-10:]
                recent_median = statistics.median(recent_times)

                result['statistics']['processing_times'] = {
                    'baseline_median': baseline_time,
                    'recent_median': recent_median,
                    'total_samples': len(processing_times)
                }

                if baseline_time > 0 and recent_median / baseline_time > self.thresholds['processing_time_factor']:
                    result['anomalies'].append({
                        'type': 'processing_slowdown',
                        'severity': 'warning',
                        'description': f"Processing time {recent_median/baseline_time:.1f}x slower than baseline",
                        'timestamp': datetime.now().isoformat(),
                        'details': {'baseline': baseline_time, 'recent': recent_median}
                    })

            # Batch size anomalies
            if len(batch_sizes) >= 5:
                normal_batch_size = statistics.median(batch_sizes[:-3])
                recent_batch_sizes = batch_sizes[-3:]

                result['statistics']['batch_sizes'] = {
                    'normal_size': normal_batch_size,
                    'recent_sizes': recent_batch_sizes,
                    'total_batches': len(batch_sizes)
                }

                for size in recent_batch_sizes:
                    if normal_batch_size > 0:
                        size_ratio = abs(size - normal_batch_size) / normal_batch_size
                        if size_ratio > self.thresholds['batch_size_deviation']:
                            result['anomalies'].append({
                                'type': 'batch_size_anomaly',
                                'severity': 'info',
                                'description': f"Unusual batch size {size} (normal: {normal_batch_size})",
                                'timestamp': datetime.now().isoformat(),
                                'details': {'normal_size': normal_batch_size, 'anomalous_size': size}
                            })

        except Exception as e:
            result['anomalies'].append({
                'type': 'performance_analysis_error',
                'severity': 'warning',
                'description': f"Error analyzing performance: {str(e)}",
                'timestamp': datetime.now().isoformat()
            })

        return result

    def _detect_quality_anomalies(self) -> Dict:
        """Detect quality anomalies."""
        result = {'anomalies': [], 'statistics': {}}

        quality_scores = list(self.baseline_data['quality_scores'])
        if len(quality_scores) < 10:
            return result

        try:
            baseline_quality = statistics.mean(quality_scores[:-10]) if len(quality_scores) > 10 else statistics.mean(quality_scores)
            recent_quality = statistics.mean(quality_scores[-10:])

            result['statistics'] = {
                'baseline_quality': baseline_quality,
                'recent_quality': recent_quality,
                'total_samples': len(quality_scores)
            }

            # Detect quality degradation
            quality_drop = baseline_quality - recent_quality
            if quality_drop > self.thresholds['quality_score_drop']:
                result['anomalies'].append({
                    'type': 'quality_degradation',
                    'severity': 'warning',
                    'description': f"Quality score dropped by {quality_drop:.3f} ({baseline_quality:.3f} → {recent_quality:.3f})",
                    'timestamp': datetime.now().isoformat(),
                    'details': {'baseline': baseline_quality, 'recent': recent_quality, 'drop': quality_drop}
                })

            # Detect quality variance anomaly
            if len(quality_scores) > 20:
                quality_std = statistics.stdev(quality_scores[-20:])
                if quality_std > 0.2:  # High variance in quality
                    result['anomalies'].append({
                        'type': 'quality_variance_spike',
                        'severity': 'info',
                        'description': f"High quality score variance detected (σ={quality_std:.3f})",
                        'timestamp': datetime.now().isoformat(),
                        'details': {'std_dev': quality_std}
                    })

        except Exception as e:
            result['anomalies'].append({
                'type': 'quality_analysis_error',
                'severity': 'warning',
                'description': f"Error analyzing quality: {str(e)}",
                'timestamp': datetime.now().isoformat()
            })

        return result

    def _detect_system_anomalies(self) -> Dict:
        """Detect system-level anomalies."""
        result = {'anomalies': [], 'statistics': {}}

        success_rates = list(self.baseline_data['success_rates'])
        error_counts = list(self.baseline_data['error_counts'])

        try:
            # Success rate anomalies
            if len(success_rates) >= 5:
                baseline_success = statistics.mean(success_rates[:-3]) if len(success_rates) > 3 else statistics.mean(success_rates)
                recent_success = statistics.mean(success_rates[-3:])

                result['statistics']['success_rates'] = {
                    'baseline': baseline_success,
                    'recent': recent_success,
                    'total_batches': len(success_rates)
                }

                success_drop = baseline_success - recent_success
                if success_drop > self.thresholds['success_rate_drop']:
                    result['anomalies'].append({
                        'type': 'success_rate_drop',
                        'severity': 'warning',
                        'description': f"Success rate dropped by {success_drop:.1%} ({baseline_success:.1%} → {recent_success:.1%})",
                        'timestamp': datetime.now().isoformat(),
                        'details': {'baseline': baseline_success, 'recent': recent_success, 'drop': success_drop}
                    })

            # Error rate anomalies
            if len(error_counts) >= 5:
                baseline_errors = statistics.mean(error_counts[:-3]) if len(error_counts) > 3 else statistics.mean(error_counts)
                recent_errors = statistics.mean(error_counts[-3:])

                result['statistics']['error_rates'] = {
                    'baseline_errors': baseline_errors,
                    'recent_errors': recent_errors,
                    'total_batches': len(error_counts)
                }

                if recent_errors > baseline_errors + self.thresholds['error_rate_spike']:
                    result['anomalies'].append({
                        'type': 'error_rate_spike',
                        'severity': 'warning',
                        'description': f"Error rate spiked from {baseline_errors:.1f} to {recent_errors:.1f} per batch",
                        'timestamp': datetime.now().isoformat(),
                        'details': {'baseline': baseline_errors, 'recent': recent_errors}
                    })

        except Exception as e:
            result['anomalies'].append({
                'type': 'system_analysis_error',
                'severity': 'warning',
                'description': f"Error analyzing system patterns: {str(e)}",
                'timestamp': datetime.now().isoformat()
            })

        return result

    def get_anomaly_summary(self) -> Dict:
        """Get summary of detected anomalies."""
        try:
            session_duration = (datetime.now() - self.session_data['start_time']).total_seconds()

            # Categorize anomalies by type
            anomaly_categories = defaultdict(list)
            for anomaly in self.session_data['anomalies_detected']:
                category = anomaly.get('type', 'unknown')
                anomaly_categories[category].append(anomaly)

            # Calculate statistics
            total_anomalies = len(self.session_data['anomalies_detected'])
            critical_anomalies = sum(1 for a in self.session_data['anomalies_detected'] if a.get('severity') == 'critical')
            warning_anomalies = sum(1 for a in self.session_data['anomalies_detected'] if a.get('severity') == 'warning')

            return {
                'timestamp': datetime.now().isoformat(),
                'session_duration_seconds': session_duration,
                'total_anomalies': total_anomalies,
                'severity_breakdown': {
                    'critical': critical_anomalies,
                    'warning': warning_anomalies,
                    'info': total_anomalies - critical_anomalies - warning_anomalies
                },
                'anomaly_categories': dict(anomaly_categories),
                'data_points_analyzed': {
                    'confidence_scores': len(self.baseline_data['confidence_scores']),
                    'processing_times': len(self.baseline_data['processing_times']),
                    'success_rates': len(self.baseline_data['success_rates']),
                    'quality_scores': len(self.baseline_data['quality_scores'])
                },
                'system_health': self._assess_system_health(),
                'recommendations': self._generate_anomaly_recommendations()
            }

        except Exception as e:
            return {
                'timestamp': datetime.now().isoformat(),
                'error': f"Error generating anomaly summary: {str(e)}",
                'session_anomalies': len(self.session_data['anomalies_detected'])
            }

    def _assess_system_health(self) -> str:
        """Assess overall system health based on anomalies."""
        total_anomalies = len(self.session_data['anomalies_detected'])
        critical_anomalies = sum(1 for a in self.session_data['anomalies_detected'] if a.get('severity') == 'critical')
        warning_anomalies = sum(1 for a in self.session_data['anomalies_detected'] if a.get('severity') == 'warning')

        if critical_anomalies > 0:
            return 'critical'
        elif warning_anomalies > 3:
            return 'degraded'
        elif warning_anomalies > 0 or total_anomalies > 5:
            return 'caution'
        else:
            return 'healthy'

    def _generate_anomaly_recommendations(self) -> List[str]:
        """Generate recommendations based on detected anomalies."""
        recommendations = []
        anomaly_types = [a.get('type', '') for a in self.session_data['anomalies_detected']]

        # Confidence-related recommendations
        if any('confidence' in atype for atype in anomaly_types):
            recommendations.append("Review confidence calibration and threshold settings")

        # Performance-related recommendations
        if any('processing_slowdown' in atype for atype in anomaly_types):
            recommendations.append("Investigate system performance and resource usage")

        # Quality-related recommendations
        if any('quality' in atype for atype in anomaly_types):
            recommendations.append("Review result quality standards and validation rules")

        # System-related recommendations
        if any('error_rate' in atype for atype in anomaly_types):
            recommendations.append("Investigate error sources and improve error handling")

        if any('success_rate' in atype for atype in anomaly_types):
            recommendations.append("Review processing logic and match criteria")

        if not recommendations:
            recommendations.append("System operating within normal parameters - maintain monitoring")

        return recommendations

if __name__ == "__main__":
    # Test the anomaly detector
    print("Testing Anomaly Detector...")

    detector = AnomalyDetector()

    # Simulate processing results
    print("1. Recording processing results...")
    import random

    # Record normal results
    for i in range(50):
        result = {
            'match_result': random.choice(['YES', 'LIKELY', 'UNCERTAIN', 'NO']),
            'confidence': random.randint(60, 95),
            'quality_score': random.uniform(0.7, 1.0)
        }
        processing_time = random.uniform(1.0, 3.0)
        detector.record_processing_result(result, processing_time)

    # Record some anomalous results
    for i in range(5):
        result = {
            'match_result': 'UNCERTAIN',
            'confidence': random.randint(20, 40),  # Low confidence
            'quality_score': random.uniform(0.2, 0.4)  # Low quality
        }
        processing_time = random.uniform(10.0, 15.0)  # Slow processing
        detector.record_processing_result(result, processing_time)

    # Record batch completions
    for i in range(10):
        batch_stats = {
            'total': 10,
            'successes': random.randint(6, 9),
            'batch_size': random.randint(8, 12),
            'errors': random.randint(0, 2)
        }
        detector.record_batch_completion(batch_stats)

    print("2. Detecting anomalies...")
    anomaly_report = detector.detect_anomalies()
    print(f"   Anomalies detected: {len(anomaly_report['anomalies_detected'])}")
    print(f"   Critical: {anomaly_report['severity_counts']['critical']}")
    print(f"   Warning: {anomaly_report['severity_counts']['warning']}")

    print("3. Generating anomaly summary...")
    summary = detector.get_anomaly_summary()
    print(f"   System health: {summary['system_health']}")
    print(f"   Recommendations: {len(summary['recommendations'])}")

    for i, rec in enumerate(summary['recommendations'], 1):
        print(f"     {i}. {rec}")

    print("Anomaly Detector test completed.")