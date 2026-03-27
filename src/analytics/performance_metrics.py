"""
Performance Metrics Tracker for Parts Agent

Monitors system performance, processing efficiency, and resource utilization.
Provides real-time metrics and performance optimization insights.
"""

import psutil
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import deque
import json
from pathlib import Path

class PerformanceTracker:
    """
    Real-time performance monitoring and metrics collection.

    Features:
    - CPU and memory usage tracking
    - Processing speed monitoring
    - Chrome browser resource usage
    - Excel file access performance
    - Network request timing
    - Error rate tracking
    """

    def __init__(self):
        self.data_dir = Path(__file__).parent.parent.parent / "data"
        self.metrics_file = self.data_dir / "performance_metrics.json"
        self.data_dir.mkdir(exist_ok=True)

        # Performance data storage
        self.metrics = {
            "system": deque(maxlen=1000),  # System performance samples
            "processing": deque(maxlen=500),  # Processing performance samples
            "network": deque(maxlen=200),  # Network timing samples
            "errors": deque(maxlen=100),  # Error tracking
            "sessions": []  # Processing session summaries
        }

        # Current session tracking
        self.current_session = None
        self.session_start_time = None
        self.monitoring_active = False
        self.monitor_thread = None
        self.lock = threading.Lock()

        # Load historical data
        self._load_metrics()

        # Chrome process tracking
        self.chrome_processes = []
        self.last_chrome_scan = None

    def _load_metrics(self):
        """Load historical metrics data."""
        try:
            if self.metrics_file.exists():
                with open(self.metrics_file, 'r') as f:
                    data = json.load(f)

                # Convert lists back to deques
                for key in ["system", "processing", "network", "errors"]:
                    if key in data:
                        self.metrics[key] = deque(data[key], maxlen=self.metrics[key].maxlen)

                if "sessions" in data:
                    self.metrics["sessions"] = data["sessions"][-50:]  # Keep last 50 sessions

        except Exception as e:
            print(f"Failed to load performance metrics: {e}")

    def _save_metrics(self):
        """Save metrics data to file."""
        try:
            # Convert deques to lists for JSON serialization
            data = {
                "system": list(self.metrics["system"]),
                "processing": list(self.metrics["processing"]),
                "network": list(self.metrics["network"]),
                "errors": list(self.metrics["errors"]),
                "sessions": self.metrics["sessions"],
                "last_updated": datetime.now().isoformat()
            }

            with open(self.metrics_file, 'w') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            print(f"Failed to save performance metrics: {e}")

    def start_monitoring(self, interval: float = 5.0):
        """Start continuous performance monitoring."""
        if self.monitoring_active:
            return

        self.monitoring_active = True
        self.monitor_thread = threading.Thread(
            target=self._monitoring_loop,
            args=(interval,),
            daemon=True
        )
        self.monitor_thread.start()

    def stop_monitoring(self):
        """Stop performance monitoring."""
        self.monitoring_active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
        self._save_metrics()

    def _monitoring_loop(self, interval: float):
        """Main monitoring loop."""
        while self.monitoring_active:
            try:
                self._collect_system_metrics()
                self._update_chrome_processes()
                time.sleep(interval)
            except Exception as e:
                print(f"Error in monitoring loop: {e}")
                time.sleep(interval)

    def _collect_system_metrics(self):
        """Collect current system performance metrics."""
        try:
            with self.lock:
                timestamp = datetime.now().isoformat()

                # System metrics
                cpu_percent = psutil.cpu_percent(interval=None)
                memory = psutil.virtual_memory()
                disk = psutil.disk_usage('/')

                system_metric = {
                    "timestamp": timestamp,
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "memory_available_gb": memory.available / (1024**3),
                    "disk_percent": disk.percent,
                    "chrome_processes": len(self.chrome_processes),
                    "chrome_memory_mb": self._get_chrome_memory_usage()
                }

                self.metrics["system"].append(system_metric)

        except Exception as e:
            self.record_error("system_monitoring", str(e))

    def _update_chrome_processes(self):
        """Update Chrome process tracking."""
        try:
            # Only scan every 30 seconds to avoid overhead
            now = datetime.now()
            if self.last_chrome_scan and (now - self.last_chrome_scan).seconds < 30:
                return

            self.chrome_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
                try:
                    if 'chrome' in proc.info['name'].lower():
                        self.chrome_processes.append(proc)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            self.last_chrome_scan = now

        except Exception as e:
            pass  # Silent fail for Chrome monitoring

    def _get_chrome_memory_usage(self) -> float:
        """Get total Chrome memory usage in MB."""
        try:
            total_memory = 0
            for proc in self.chrome_processes:
                try:
                    memory_info = proc.memory_info()
                    total_memory += memory_info.rss
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass

            return total_memory / (1024 * 1024)  # Convert to MB

        except Exception:
            return 0

    def start_processing_session(self, sheet_name: str, total_rows: int, enhancement_type: str = "standard"):
        """Start tracking a processing session."""
        with self.lock:
            self.current_session = {
                "sheet_name": sheet_name,
                "total_rows": total_rows,
                "enhancement_type": enhancement_type,
                "start_time": datetime.now(),
                "rows_processed": 0,
                "errors": 0,
                "network_requests": 0,
                "total_request_time": 0,
                "success_count": 0,
                "likely_count": 0,
                "uncertain_count": 0,
                "no_count": 0,
                "avg_confidence": 0
            }
            self.session_start_time = time.time()

    def record_row_processed(self, result: str, confidence: int = None, request_time: float = None):
        """Record processing of a single row."""
        if not self.current_session:
            return

        with self.lock:
            self.current_session["rows_processed"] += 1

            # Update result counts
            if result == "YES":
                self.current_session["success_count"] += 1
            elif result == "LIKELY":
                self.current_session["likely_count"] += 1
            elif result == "UNCERTAIN":
                self.current_session["uncertain_count"] += 1
            elif result == "NO":
                self.current_session["no_count"] += 1

            # Track network timing
            if request_time:
                self.current_session["network_requests"] += 1
                self.current_session["total_request_time"] += request_time

                # Record individual network sample
                self.metrics["network"].append({
                    "timestamp": datetime.now().isoformat(),
                    "request_time": request_time,
                    "sheet": self.current_session["sheet_name"]
                })

            # Record processing sample
            current_time = time.time()
            session_duration = current_time - self.session_start_time
            processing_speed = self.current_session["rows_processed"] / session_duration if session_duration > 0 else 0

            self.metrics["processing"].append({
                "timestamp": datetime.now().isoformat(),
                "sheet": self.current_session["sheet_name"],
                "rows_per_second": processing_speed,
                "cumulative_rows": self.current_session["rows_processed"],
                "enhancement_type": self.current_session["enhancement_type"]
            })

    def record_error(self, error_type: str, error_message: str):
        """Record an error occurrence."""
        with self.lock:
            error_record = {
                "timestamp": datetime.now().isoformat(),
                "error_type": error_type,
                "message": error_message,
                "sheet": self.current_session["sheet_name"] if self.current_session else None
            }

            self.metrics["errors"].append(error_record)

            if self.current_session:
                self.current_session["errors"] += 1

    def finish_processing_session(self):
        """Finish and record the current processing session."""
        if not self.current_session:
            return

        with self.lock:
            session = self.current_session.copy()
            session["end_time"] = datetime.now()
            session["duration_seconds"] = (session["end_time"] - session["start_time"]).total_seconds()

            # Calculate final metrics
            if session["rows_processed"] > 0:
                session["avg_processing_speed"] = session["rows_processed"] / session["duration_seconds"] if session["duration_seconds"] > 0 else 0
                session["success_rate"] = ((session["success_count"] + session["likely_count"]) / session["rows_processed"]) * 100
                session["error_rate"] = (session["errors"] / session["rows_processed"]) * 100

            if session["network_requests"] > 0:
                session["avg_request_time"] = session["total_request_time"] / session["network_requests"]

            # Store session summary
            self.metrics["sessions"].append(session)

            # Clear current session
            self.current_session = None
            self.session_start_time = None

            self._save_metrics()

    def get_performance_summary(self) -> Dict:
        """Get comprehensive performance summary."""
        with self.lock:
            summary = {
                "current_status": self._get_current_status(),
                "system_performance": self._get_system_performance(),
                "processing_performance": self._get_processing_performance(),
                "network_performance": self._get_network_performance(),
                "error_analysis": self._get_error_analysis(),
                "session_history": self._get_session_history(),
                "optimization_recommendations": [],
                "timestamp": datetime.now().isoformat()
            }

            # Generate optimization recommendations
            summary["optimization_recommendations"] = self._generate_optimization_recommendations(summary)

            return summary

    def _get_current_status(self) -> Dict:
        """Get current session status."""
        if not self.current_session:
            return {"status": "idle"}

        current_time = time.time()
        session_duration = current_time - self.session_start_time if self.session_start_time else 0

        return {
            "status": "processing",
            "sheet": self.current_session["sheet_name"],
            "rows_processed": self.current_session["rows_processed"],
            "total_rows": self.current_session["total_rows"],
            "completion_percentage": (self.current_session["rows_processed"] / self.current_session["total_rows"]) * 100,
            "session_duration": session_duration,
            "current_speed": self.current_session["rows_processed"] / session_duration if session_duration > 0 else 0,
            "errors_this_session": self.current_session["errors"],
            "enhancement_type": self.current_session["enhancement_type"]
        }

    def _get_system_performance(self) -> Dict:
        """Analyze system performance metrics."""
        if not self.metrics["system"]:
            return {"error": "No system metrics available"}

        recent_metrics = list(self.metrics["system"])[-20:]  # Last 20 samples

        cpu_values = [m["cpu_percent"] for m in recent_metrics]
        memory_values = [m["memory_percent"] for m in recent_metrics]

        return {
            "current_cpu": recent_metrics[-1]["cpu_percent"] if recent_metrics else None,
            "avg_cpu": sum(cpu_values) / len(cpu_values) if cpu_values else None,
            "peak_cpu": max(cpu_values) if cpu_values else None,
            "current_memory": recent_metrics[-1]["memory_percent"] if recent_metrics else None,
            "avg_memory": sum(memory_values) / len(memory_values) if memory_values else None,
            "chrome_processes": recent_metrics[-1]["chrome_processes"] if recent_metrics else 0,
            "chrome_memory_mb": recent_metrics[-1]["chrome_memory_mb"] if recent_metrics else 0,
            "monitoring_active": self.monitoring_active
        }

    def _get_processing_performance(self) -> Dict:
        """Analyze processing performance."""
        if not self.metrics["processing"]:
            return {"error": "No processing metrics available"}

        recent_processing = list(self.metrics["processing"])[-50:]  # Last 50 samples

        speeds = [p["rows_per_second"] for p in recent_processing if p["rows_per_second"] > 0]

        # Analyze by enhancement type
        standard_speeds = [p["rows_per_second"] for p in recent_processing if p["enhancement_type"] == "standard" and p["rows_per_second"] > 0]
        enhanced_speeds = [p["rows_per_second"] for p in recent_processing if p["enhancement_type"] == "enhanced" and p["rows_per_second"] > 0]

        performance = {
            "current_speed": speeds[-1] if speeds else None,
            "avg_speed": sum(speeds) / len(speeds) if speeds else None,
            "peak_speed": max(speeds) if speeds else None,
            "total_samples": len(speeds),
            "enhancement_comparison": {}
        }

        if standard_speeds and enhanced_speeds:
            performance["enhancement_comparison"] = {
                "standard_avg": sum(standard_speeds) / len(standard_speeds),
                "enhanced_avg": sum(enhanced_speeds) / len(enhanced_speeds),
                "improvement_factor": (sum(enhanced_speeds) / len(enhanced_speeds)) / (sum(standard_speeds) / len(standard_speeds))
            }

        return performance

    def _get_network_performance(self) -> Dict:
        """Analyze network performance."""
        if not self.metrics["network"]:
            return {"error": "No network metrics available"}

        recent_network = list(self.metrics["network"])[-100:]  # Last 100 requests

        request_times = [n["request_time"] for n in recent_network]

        return {
            "avg_request_time": sum(request_times) / len(request_times) if request_times else None,
            "min_request_time": min(request_times) if request_times else None,
            "max_request_time": max(request_times) if request_times else None,
            "total_requests": len(request_times),
            "requests_per_minute": self._calculate_requests_per_minute(recent_network),
            "slow_requests": len([t for t in request_times if t > 10]) if request_times else 0
        }

    def _calculate_requests_per_minute(self, network_data: List[Dict]) -> float:
        """Calculate requests per minute rate."""
        if len(network_data) < 2:
            return 0

        try:
            # Calculate time span of recent requests
            start_time = datetime.fromisoformat(network_data[0]["timestamp"])
            end_time = datetime.fromisoformat(network_data[-1]["timestamp"])
            duration_minutes = (end_time - start_time).total_seconds() / 60

            return len(network_data) / duration_minutes if duration_minutes > 0 else 0

        except Exception:
            return 0

    def _get_error_analysis(self) -> Dict:
        """Analyze error patterns."""
        if not self.metrics["errors"]:
            return {"total_errors": 0}

        recent_errors = list(self.metrics["errors"])[-50:]  # Last 50 errors

        # Count errors by type
        error_types = {}
        for error in recent_errors:
            error_type = error["error_type"]
            error_types[error_type] = error_types.get(error_type, 0) + 1

        # Recent error rate
        recent_time = datetime.now() - timedelta(hours=1)
        recent_errors_count = len([
            e for e in recent_errors
            if datetime.fromisoformat(e["timestamp"]) > recent_time
        ])

        return {
            "total_errors": len(recent_errors),
            "recent_hour_errors": recent_errors_count,
            "error_types": error_types,
            "most_common_error": max(error_types.items(), key=lambda x: x[1])[0] if error_types else None
        }

    def _get_session_history(self) -> Dict:
        """Get processing session history."""
        sessions = self.metrics["sessions"][-10:]  # Last 10 sessions

        if not sessions:
            return {"total_sessions": 0}

        # Calculate session statistics
        durations = [s.get("duration_seconds", 0) for s in sessions if s.get("duration_seconds")]
        success_rates = [s.get("success_rate", 0) for s in sessions if s.get("success_rate")]
        processing_speeds = [s.get("avg_processing_speed", 0) for s in sessions if s.get("avg_processing_speed")]

        return {
            "total_sessions": len(sessions),
            "avg_duration": sum(durations) / len(durations) if durations else 0,
            "avg_success_rate": sum(success_rates) / len(success_rates) if success_rates else 0,
            "avg_processing_speed": sum(processing_speeds) / len(processing_speeds) if processing_speeds else 0,
            "recent_sessions": [
                {
                    "sheet": s["sheet_name"],
                    "rows": s.get("rows_processed", 0),
                    "duration": s.get("duration_seconds", 0),
                    "success_rate": s.get("success_rate", 0),
                    "enhancement": s.get("enhancement_type", "standard")
                }
                for s in sessions[-5:]  # Last 5 sessions
            ]
        }

    def _generate_optimization_recommendations(self, summary: Dict) -> List[str]:
        """Generate performance optimization recommendations."""
        recommendations = []

        # System performance recommendations
        system = summary.get("system_performance", {})
        if system.get("avg_cpu", 0) > 80:
            recommendations.append("High CPU usage detected - consider reducing concurrent operations")

        if system.get("avg_memory", 0) > 85:
            recommendations.append("High memory usage - consider restarting Chrome processes periodically")

        if system.get("chrome_memory_mb", 0) > 2000:  # 2GB
            recommendations.append("Chrome using excessive memory - implement more frequent browser restarts")

        # Network performance recommendations
        network = summary.get("network_performance", {})
        if network.get("avg_request_time", 0) > 8:
            recommendations.append("Network requests are slow - check internet connection or RockAuto performance")

        if network.get("slow_requests", 0) > 10:
            recommendations.append("Many slow requests detected - consider implementing request timeout optimization")

        # Processing performance recommendations
        processing = summary.get("processing_performance", {})
        if processing.get("avg_speed", 0) < 5:  # Less than 5 rows per second
            recommendations.append("Low processing speed - investigate bottlenecks in comparison engine")

        # Error analysis recommendations
        errors = summary.get("error_analysis", {})
        if errors.get("recent_hour_errors", 0) > 5:
            recommendations.append("High error rate - review recent error logs and implement fixes")

        return recommendations

    def get_real_time_metrics(self) -> Dict:
        """Get current real-time performance metrics."""
        with self.lock:
            current_status = self._get_current_status()

            # Get latest system metrics
            latest_system = list(self.metrics["system"])[-1] if self.metrics["system"] else {}

            # Get recent processing speed
            recent_processing = list(self.metrics["processing"])[-5:] if self.metrics["processing"] else []
            current_speed = recent_processing[-1]["rows_per_second"] if recent_processing else 0

            return {
                "timestamp": datetime.now().isoformat(),
                "processing_status": current_status,
                "system": {
                    "cpu_percent": latest_system.get("cpu_percent", 0),
                    "memory_percent": latest_system.get("memory_percent", 0),
                    "chrome_memory_mb": latest_system.get("chrome_memory_mb", 0)
                },
                "performance": {
                    "current_speed": current_speed,
                    "processing_active": current_status["status"] == "processing"
                }
            }

    def export_performance_report(self, filepath: str) -> bool:
        """Export comprehensive performance report."""
        try:
            report = self.get_performance_summary()
            with open(filepath, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            return True
        except Exception as e:
            print(f"Failed to export performance report: {e}")
            return False