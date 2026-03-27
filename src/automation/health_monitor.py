"""
Health Monitor
Advanced Integration & Automation (Priority 5)

System health monitoring and alerting:
- Real-time system health assessment
- Performance threshold monitoring
- Automated alert generation
- Health trend analysis
- Predictive health warnings
"""

import json
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any
from enum import Enum
from collections import deque
import sys

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from analytics.performance_metrics import PerformanceTracker
from validation.anomaly_detector import AnomalyDetector

class HealthStatus(Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"

class AlertSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

class HealthAlert:
    """Represents a system health alert."""

    def __init__(self, severity: AlertSeverity, component: str, message: str,
                 details: Dict = None):
        self.id = f"alert_{int(time.time() * 1000)}"
        self.severity = severity
        self.component = component
        self.message = message
        self.details = details or {}
        self.timestamp = datetime.now().isoformat()
        self.acknowledged = False
        self.resolved = False

    def to_dict(self) -> Dict:
        return {
            'id': self.id,
            'severity': self.severity.value,
            'component': self.component,
            'message': self.message,
            'details': self.details,
            'timestamp': self.timestamp,
            'acknowledged': self.acknowledged,
            'resolved': self.resolved
        }

class HealthMonitor:
    """Advanced system health monitoring and alerting system."""

    def __init__(self, excel_path: str = None):
        """Initialize the health monitor."""
        if excel_path is None:
            excel_path = str(Path(__file__).parent.parent.parent / "FISHER SKP INTERCHANGE 20260302.xlsx")

        self.excel_path = excel_path
        self.performance_tracker = PerformanceTracker()
        self.anomaly_detector = AnomalyDetector(excel_path)

        # Health thresholds
        self.thresholds = {
            'cpu_warning': 80.0,
            'cpu_critical': 95.0,
            'memory_warning': 85.0,
            'memory_critical': 95.0,
            'disk_warning': 90.0,
            'disk_critical': 98.0,
            'error_rate_warning': 0.1,  # 10%
            'error_rate_critical': 0.25,  # 25%
            'processing_slowdown_warning': 2.0,  # 2x slower
            'processing_slowdown_critical': 5.0,  # 5x slower
            'success_rate_warning': 0.7,  # Below 70%
            'success_rate_critical': 0.5  # Below 50%
        }

        # Monitoring configuration
        self.config = {
            'monitoring_interval': 30,  # seconds
            'alert_retention_hours': 24,
            'health_check_components': [
                'system_resources',
                'processing_performance',
                'data_quality',
                'anomaly_detection',
                'scheduler_health'
            ]
        }

        # Health data
        self.current_health = {
            'overall_status': HealthStatus.UNKNOWN,
            'component_health': {},
            'last_check': None,
            'check_count': 0
        }

        # Alert management
        self.active_alerts = {}  # Dict[str, HealthAlert]
        self.alert_history = deque(maxlen=1000)
        self.alert_callbacks = []  # List[Callable[[HealthAlert], None]]

        # Historical data
        self.health_history = deque(maxlen=2880)  # 24 hours at 30-second intervals

        # Monitoring thread
        self.monitor_thread = None
        self.monitoring_active = False
        self.lock = threading.Lock()

        # Statistics
        self.stats = {
            'monitoring_start_time': None,
            'total_checks': 0,
            'total_alerts': 0,
            'critical_alerts': 0,
            'warning_alerts': 0,
            'resolved_alerts': 0
        }

        print("[HEALTH_MONITOR] Initialized with comprehensive health monitoring")

    def start_monitoring(self):
        """Start health monitoring."""
        with self.lock:
            if self.monitoring_active:
                print("Health monitoring is already active")
                return

            self.monitoring_active = True
            self.stats['monitoring_start_time'] = datetime.now().isoformat()

            self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
            self.monitor_thread.start()

            print("[HEALTH_MONITOR] Health monitoring started")

    def stop_monitoring(self):
        """Stop health monitoring."""
        with self.lock:
            if not self.monitoring_active:
                return

            self.monitoring_active = False

            if self.monitor_thread and self.monitor_thread.is_alive():
                self.monitor_thread.join(timeout=5)

            print("[HEALTH_MONITOR] Health monitoring stopped")

    def register_alert_callback(self, callback: Callable[[HealthAlert], None]):
        """Register a callback function for alert notifications."""
        self.alert_callbacks.append(callback)

    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an active alert."""
        with self.lock:
            if alert_id in self.active_alerts:
                self.active_alerts[alert_id].acknowledged = True
                return True
            return False

    def resolve_alert(self, alert_id: str) -> bool:
        """Mark an alert as resolved."""
        with self.lock:
            if alert_id in self.active_alerts:
                alert = self.active_alerts[alert_id]
                alert.resolved = True
                self.alert_history.append(alert)
                del self.active_alerts[alert_id]
                self.stats['resolved_alerts'] += 1
                return True
            return False

    def get_health_status(self) -> Dict:
        """Get current health status."""
        with self.lock:
            return {
                'overall_status': self.current_health['overall_status'].value,
                'component_health': {
                    comp: status.value if hasattr(status, 'value') else status
                    for comp, status in self.current_health['component_health'].items()
                },
                'last_check': self.current_health['last_check'],
                'check_count': self.current_health['check_count'],
                'active_alerts': len(self.active_alerts),
                'monitoring_active': self.monitoring_active
            }

    def get_active_alerts(self) -> List[Dict]:
        """Get all active alerts."""
        with self.lock:
            return [alert.to_dict() for alert in self.active_alerts.values()]

    def _monitoring_loop(self):
        """Main health monitoring loop."""
        print("[HEALTH_MONITOR] Monitoring loop started")

        while self.monitoring_active:
            try:
                # Perform health check
                self._perform_health_check()

                # Clean up old alerts
                self._cleanup_old_alerts()

                # Sleep until next check
                time.sleep(self.config['monitoring_interval'])

            except Exception as e:
                print(f"[HEALTH_MONITOR] Error in monitoring loop: {e}")
                time.sleep(30)

        print("[HEALTH_MONITOR] Monitoring loop stopped")

    def _perform_health_check(self):
        """Perform comprehensive health check."""
        with self.lock:
            check_time = datetime.now()
            component_health = {}

            # Check each component
            for component in self.config['health_check_components']:
                try:
                    if component == 'system_resources':
                        component_health[component] = self._check_system_resources()
                    elif component == 'processing_performance':
                        component_health[component] = self._check_processing_performance()
                    elif component == 'data_quality':
                        component_health[component] = self._check_data_quality()
                    elif component == 'anomaly_detection':
                        component_health[component] = self._check_anomaly_status()
                    elif component == 'scheduler_health':
                        component_health[component] = self._check_scheduler_health()

                except Exception as e:
                    print(f"[HEALTH_MONITOR] Error checking {component}: {e}")
                    component_health[component] = HealthStatus.UNKNOWN

            # Calculate overall health
            overall_status = self._calculate_overall_health(component_health)

            # Update current health
            self.current_health = {
                'overall_status': overall_status,
                'component_health': component_health,
                'last_check': check_time.isoformat(),
                'check_count': self.current_health['check_count'] + 1
            }

            # Store in history
            health_snapshot = {
                'timestamp': check_time.isoformat(),
                'overall_status': overall_status.value,
                'component_health': {k: v.value for k, v in component_health.items()}
            }
            self.health_history.append(health_snapshot)

            # Update statistics
            self.stats['total_checks'] += 1

    def _check_system_resources(self) -> HealthStatus:
        """Check system resource health."""
        try:
            metrics = self.performance_tracker.get_real_time_metrics()
            system_metrics = metrics.get('system', {})

            cpu_usage = system_metrics.get('cpu_percent', 0)
            memory_usage = system_metrics.get('memory_percent', 0)

            # Check CPU
            if cpu_usage >= self.thresholds['cpu_critical']:
                self._create_alert(AlertSeverity.CRITICAL, 'system_resources',
                                 f"Critical CPU usage: {cpu_usage:.1f}%",
                                 {'cpu_usage': cpu_usage, 'threshold': self.thresholds['cpu_critical']})
                return HealthStatus.CRITICAL

            elif cpu_usage >= self.thresholds['cpu_warning']:
                self._create_alert(AlertSeverity.WARNING, 'system_resources',
                                 f"High CPU usage: {cpu_usage:.1f}%",
                                 {'cpu_usage': cpu_usage, 'threshold': self.thresholds['cpu_warning']})
                return HealthStatus.WARNING

            # Check Memory
            if memory_usage >= self.thresholds['memory_critical']:
                self._create_alert(AlertSeverity.CRITICAL, 'system_resources',
                                 f"Critical memory usage: {memory_usage:.1f}%",
                                 {'memory_usage': memory_usage, 'threshold': self.thresholds['memory_critical']})
                return HealthStatus.CRITICAL

            elif memory_usage >= self.thresholds['memory_warning']:
                self._create_alert(AlertSeverity.WARNING, 'system_resources',
                                 f"High memory usage: {memory_usage:.1f}%",
                                 {'memory_usage': memory_usage, 'threshold': self.thresholds['memory_warning']})
                return HealthStatus.WARNING

            return HealthStatus.HEALTHY

        except Exception as e:
            self._create_alert(AlertSeverity.WARNING, 'system_resources',
                             f"Error checking system resources: {str(e)}")
            return HealthStatus.UNKNOWN

    def _check_processing_performance(self) -> HealthStatus:
        """Check processing performance health."""
        try:
            # This would integrate with actual processing metrics
            # For now, simulate based on performance tracker data
            metrics = self.performance_tracker.get_real_time_metrics()
            performance = metrics.get('performance', {})

            current_speed = performance.get('current_speed', 0)

            # Simulate baseline speed (would be calculated from historical data)
            baseline_speed = 1.5  # rows per second

            if baseline_speed > 0:
                speed_ratio = baseline_speed / max(current_speed, 0.1)

                if speed_ratio >= self.thresholds['processing_slowdown_critical']:
                    self._create_alert(AlertSeverity.CRITICAL, 'processing_performance',
                                     f"Critical processing slowdown: {speed_ratio:.1f}x slower than baseline",
                                     {'current_speed': current_speed, 'baseline_speed': baseline_speed})
                    return HealthStatus.CRITICAL

                elif speed_ratio >= self.thresholds['processing_slowdown_warning']:
                    self._create_alert(AlertSeverity.WARNING, 'processing_performance',
                                     f"Processing slowdown detected: {speed_ratio:.1f}x slower than baseline",
                                     {'current_speed': current_speed, 'baseline_speed': baseline_speed})
                    return HealthStatus.WARNING

            return HealthStatus.HEALTHY

        except Exception as e:
            self._create_alert(AlertSeverity.WARNING, 'processing_performance',
                             f"Error checking processing performance: {str(e)}")
            return HealthStatus.UNKNOWN

    def _check_data_quality(self) -> HealthStatus:
        """Check data quality health."""
        try:
            # This would integrate with validation system
            # For now, simulate data quality check

            # Simulated quality metrics
            quality_score = 0.85
            error_rate = 0.05

            if error_rate >= self.thresholds['error_rate_critical']:
                self._create_alert(AlertSeverity.CRITICAL, 'data_quality',
                                 f"Critical data error rate: {error_rate:.1%}",
                                 {'error_rate': error_rate, 'quality_score': quality_score})
                return HealthStatus.CRITICAL

            elif error_rate >= self.thresholds['error_rate_warning']:
                self._create_alert(AlertSeverity.WARNING, 'data_quality',
                                 f"High data error rate: {error_rate:.1%}",
                                 {'error_rate': error_rate, 'quality_score': quality_score})
                return HealthStatus.WARNING

            elif quality_score < 0.7:
                self._create_alert(AlertSeverity.WARNING, 'data_quality',
                                 f"Low data quality score: {quality_score:.1%}")
                return HealthStatus.WARNING

            return HealthStatus.HEALTHY

        except Exception as e:
            self._create_alert(AlertSeverity.WARNING, 'data_quality',
                             f"Error checking data quality: {str(e)}")
            return HealthStatus.UNKNOWN

    def _check_anomaly_status(self) -> HealthStatus:
        """Check anomaly detection status."""
        try:
            # Get recent anomaly summary
            anomaly_summary = self.anomaly_detector.get_anomaly_summary()
            system_health = anomaly_summary.get('system_health', 'unknown')

            if system_health == 'critical':
                critical_count = anomaly_summary.get('severity_breakdown', {}).get('critical', 0)
                self._create_alert(AlertSeverity.CRITICAL, 'anomaly_detection',
                                 f"Critical anomalies detected: {critical_count} critical issues",
                                 {'system_health': system_health, 'critical_count': critical_count})
                return HealthStatus.CRITICAL

            elif system_health == 'degraded':
                warning_count = anomaly_summary.get('severity_breakdown', {}).get('warning', 0)
                self._create_alert(AlertSeverity.WARNING, 'anomaly_detection',
                                 f"System performance degraded: {warning_count} warnings",
                                 {'system_health': system_health, 'warning_count': warning_count})
                return HealthStatus.WARNING

            elif system_health == 'caution':
                return HealthStatus.WARNING

            return HealthStatus.HEALTHY

        except Exception as e:
            self._create_alert(AlertSeverity.WARNING, 'anomaly_detection',
                             f"Error checking anomaly status: {str(e)}")
            return HealthStatus.UNKNOWN

    def _check_scheduler_health(self) -> HealthStatus:
        """Check scheduler health (placeholder for integration with scheduler)."""
        try:
            # This would integrate with the automation scheduler
            # For now, simulate scheduler health check

            # Simulated scheduler metrics
            scheduler_running = True
            failed_tasks = 1
            total_tasks = 10

            if not scheduler_running:
                self._create_alert(AlertSeverity.CRITICAL, 'scheduler_health',
                                 "Automation scheduler is not running")
                return HealthStatus.CRITICAL

            if total_tasks > 0:
                failure_rate = failed_tasks / total_tasks
                if failure_rate >= 0.3:  # 30% failure rate
                    self._create_alert(AlertSeverity.WARNING, 'scheduler_health',
                                     f"High scheduler task failure rate: {failure_rate:.1%}")
                    return HealthStatus.WARNING

            return HealthStatus.HEALTHY

        except Exception as e:
            self._create_alert(AlertSeverity.WARNING, 'scheduler_health',
                             f"Error checking scheduler health: {str(e)}")
            return HealthStatus.UNKNOWN

    def _calculate_overall_health(self, component_health: Dict) -> HealthStatus:
        """Calculate overall system health from component health."""
        if not component_health:
            return HealthStatus.UNKNOWN

        # Count health statuses
        status_counts = {status: 0 for status in HealthStatus}
        for status in component_health.values():
            status_counts[status] += 1

        # Determine overall status
        if status_counts[HealthStatus.CRITICAL] > 0:
            return HealthStatus.CRITICAL
        elif status_counts[HealthStatus.WARNING] > 0:
            return HealthStatus.WARNING
        elif status_counts[HealthStatus.UNKNOWN] > len(component_health) // 2:
            return HealthStatus.UNKNOWN
        else:
            return HealthStatus.HEALTHY

    def _create_alert(self, severity: AlertSeverity, component: str, message: str, details: Dict = None):
        """Create and process a new alert."""
        alert = HealthAlert(severity, component, message, details)

        # Check if similar alert already exists
        similar_alert_exists = False
        for existing_alert in self.active_alerts.values():
            if (existing_alert.component == component and
                existing_alert.severity == severity and
                not existing_alert.resolved):
                similar_alert_exists = True
                break

        if not similar_alert_exists:
            self.active_alerts[alert.id] = alert
            self.stats['total_alerts'] += 1

            if severity == AlertSeverity.CRITICAL:
                self.stats['critical_alerts'] += 1
            elif severity == AlertSeverity.WARNING:
                self.stats['warning_alerts'] += 1

            # Notify callbacks
            for callback in self.alert_callbacks:
                try:
                    callback(alert)
                except Exception as e:
                    print(f"[HEALTH_MONITOR] Error in alert callback: {e}")

    def _cleanup_old_alerts(self):
        """Clean up old resolved alerts from history."""
        current_time = datetime.now()
        retention_threshold = current_time - timedelta(hours=self.config['alert_retention_hours'])

        # Clean up alert history
        while self.alert_history:
            oldest_alert = self.alert_history[0]
            alert_time = datetime.fromisoformat(oldest_alert.timestamp)
            if alert_time < retention_threshold:
                self.alert_history.popleft()
            else:
                break

    def get_health_report(self) -> Dict:
        """Generate comprehensive health report."""
        with self.lock:
            current_time = datetime.now()

            # Calculate uptime
            uptime_seconds = 0
            if self.stats['monitoring_start_time']:
                start_time = datetime.fromisoformat(self.stats['monitoring_start_time'])
                uptime_seconds = (current_time - start_time).total_seconds()

            # Health trend analysis
            health_trend = self._analyze_health_trend()

            # Alert statistics
            alert_stats = {
                'active_alerts': len(self.active_alerts),
                'total_alerts': self.stats['total_alerts'],
                'critical_alerts': self.stats['critical_alerts'],
                'warning_alerts': self.stats['warning_alerts'],
                'resolved_alerts': self.stats['resolved_alerts'],
                'alert_history_size': len(self.alert_history)
            }

            return {
                'timestamp': current_time.isoformat(),
                'monitoring_status': {
                    'active': self.monitoring_active,
                    'uptime_seconds': uptime_seconds,
                    'uptime_hours': uptime_seconds / 3600,
                    'total_checks': self.stats['total_checks']
                },
                'current_health': self.get_health_status(),
                'health_trend': health_trend,
                'alert_statistics': alert_stats,
                'active_alerts': self.get_active_alerts(),
                'thresholds': self.thresholds.copy(),
                'recommendations': self._generate_health_recommendations()
            }

    def _analyze_health_trend(self) -> Dict:
        """Analyze health trends over time."""
        if len(self.health_history) < 2:
            return {'trend': 'insufficient_data', 'direction': 'unknown'}

        # Get recent health snapshots
        recent_snapshots = list(self.health_history)[-10:]  # Last 10 snapshots
        earlier_snapshots = list(self.health_history)[-20:-10] if len(self.health_history) >= 20 else []

        if not earlier_snapshots:
            return {'trend': 'insufficient_data', 'direction': 'unknown'}

        # Count health statuses in each period
        def count_statuses(snapshots):
            counts = {'healthy': 0, 'warning': 0, 'critical': 0, 'unknown': 0}
            for snapshot in snapshots:
                status = snapshot.get('overall_status', 'unknown')
                counts[status] += 1
            return counts

        recent_counts = count_statuses(recent_snapshots)
        earlier_counts = count_statuses(earlier_snapshots)

        # Simple trend analysis
        recent_health_score = (recent_counts['healthy'] * 3 + recent_counts['warning'] * 1 +
                              recent_counts['critical'] * 0 + recent_counts['unknown'] * 1)
        earlier_health_score = (earlier_counts['healthy'] * 3 + earlier_counts['warning'] * 1 +
                               earlier_counts['critical'] * 0 + earlier_counts['unknown'] * 1)

        if recent_health_score > earlier_health_score * 1.1:
            direction = 'improving'
        elif recent_health_score < earlier_health_score * 0.9:
            direction = 'declining'
        else:
            direction = 'stable'

        return {
            'trend': 'analyzed',
            'direction': direction,
            'recent_score': recent_health_score,
            'earlier_score': earlier_health_score,
            'sample_size': len(recent_snapshots)
        }

    def _generate_health_recommendations(self) -> List[str]:
        """Generate health improvement recommendations."""
        recommendations = []

        # Check current health status
        current_status = self.current_health['overall_status']
        if current_status == HealthStatus.CRITICAL:
            recommendations.append("System is in critical state - immediate attention required")

        elif current_status == HealthStatus.WARNING:
            recommendations.append("System warnings detected - review and address issues")

        # Check alert patterns
        if len(self.active_alerts) > 5:
            recommendations.append("Multiple active alerts - prioritize resolution")

        critical_alerts = [a for a in self.active_alerts.values() if a.severity == AlertSeverity.CRITICAL]
        if critical_alerts:
            recommendations.append(f"{len(critical_alerts)} critical alerts require immediate attention")

        # Check monitoring statistics
        if self.stats['total_checks'] > 0:
            alert_rate = self.stats['total_alerts'] / self.stats['total_checks']
            if alert_rate > 0.1:  # More than 10% of checks generate alerts
                recommendations.append("High alert rate detected - review thresholds and system performance")

        if not recommendations:
            recommendations.append("System health monitoring is operating normally")

        return recommendations

if __name__ == "__main__":
    # Test the health monitor
    print("Testing Health Monitor...")

    monitor = HealthMonitor()

    # Register a test callback
    def test_alert_callback(alert: HealthAlert):
        print(f"ALERT: [{alert.severity.value.upper()}] {alert.component}: {alert.message}")

    monitor.register_alert_callback(test_alert_callback)

    # Start monitoring
    monitor.start_monitoring()

    try:
        # Let it run for a short time
        print("Health monitoring running... (will run for 20 seconds)")
        time.sleep(20)

        # Check health status
        health_status = monitor.get_health_status()
        print(f"\nHealth Status:")
        print(f"  Overall: {health_status['overall_status']}")
        print(f"  Active alerts: {health_status['active_alerts']}")
        print(f"  Checks performed: {health_status['check_count']}")

        # Get active alerts
        alerts = monitor.get_active_alerts()
        if alerts:
            print(f"\nActive Alerts ({len(alerts)}):")
            for alert in alerts[:3]:  # Show first 3
                print(f"  - {alert['severity'].upper()}: {alert['message']}")

        # Generate health report
        report = monitor.get_health_report()
        print(f"\nHealth Report:")
        print(f"  Monitoring uptime: {report['monitoring_status']['uptime_hours']:.1f} hours")
        print(f"  Total alerts: {report['alert_statistics']['total_alerts']}")

    finally:
        # Stop monitoring
        monitor.stop_monitoring()

    print("Health Monitor test completed.")