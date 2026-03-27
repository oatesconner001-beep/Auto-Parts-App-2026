"""
Trend Analysis Engine for Parts Agent

Analyzes historical trends in processing performance, success rates, and system efficiency.
Tracks changes over time to identify improvements and bottlenecks.
"""

import json
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict
import statistics

class TrendAnalyzer:
    """
    Historical trend analysis for parts processing performance.

    Features:
    - Processing speed trends over time
    - Success rate improvements tracking
    - Performance benchmarking
    - Efficiency optimization insights
    """

    def __init__(self, excel_path: str = None):
        self.excel_path = excel_path
        self.db_path = Path(__file__).parent.parent.parent / "data" / "trends.db"
        self.data_dir = Path(__file__).parent.parent.parent / "data"

        # Ensure data directory exists
        self.data_dir.mkdir(exist_ok=True)

        # Initialize database
        self._init_database()

    def _init_database(self):
        """Initialize SQLite database for trend storage."""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            # Processing sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS processing_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME NOT NULL,
                    sheet_name TEXT NOT NULL,
                    rows_processed INTEGER NOT NULL,
                    duration_seconds REAL,
                    success_count INTEGER NOT NULL,
                    likely_count INTEGER NOT NULL,
                    uncertain_count INTEGER NOT NULL,
                    no_count INTEGER NOT NULL,
                    avg_confidence REAL,
                    error_count INTEGER DEFAULT 0,
                    enhancement_type TEXT DEFAULT 'standard'
                )
            """)

            # Daily summaries table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS daily_summaries (
                    date TEXT PRIMARY KEY,
                    total_processed INTEGER NOT NULL,
                    total_confirmed INTEGER NOT NULL,
                    avg_success_rate REAL,
                    total_duration_hours REAL,
                    processing_speed REAL,
                    enhancement_upgrades INTEGER DEFAULT 0
                )
            """)

            # Performance metrics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    timestamp DATETIME PRIMARY KEY,
                    metric_name TEXT NOT NULL,
                    metric_value REAL NOT NULL,
                    sheet_name TEXT,
                    additional_data TEXT
                )
            """)

            conn.commit()
            conn.close()

        except Exception as e:
            print(f"Failed to initialize trend database: {e}")

    def record_processing_session(self, session_data: Dict):
        """Record a processing session for trend analysis."""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO processing_sessions (
                    timestamp, sheet_name, rows_processed, duration_seconds,
                    success_count, likely_count, uncertain_count, no_count,
                    avg_confidence, error_count, enhancement_type
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                session_data.get("sheet_name", "Unknown"),
                session_data.get("rows_processed", 0),
                session_data.get("duration_seconds", 0),
                session_data.get("success_count", 0),
                session_data.get("likely_count", 0),
                session_data.get("uncertain_count", 0),
                session_data.get("no_count", 0),
                session_data.get("avg_confidence"),
                session_data.get("error_count", 0),
                session_data.get("enhancement_type", "standard")
            ))

            conn.commit()
            conn.close()

            # Update daily summary
            self._update_daily_summary()

        except Exception as e:
            print(f"Failed to record processing session: {e}")

    def record_performance_metric(self, metric_name: str, value: float, sheet_name: str = None, additional_data: Dict = None):
        """Record a performance metric for trend tracking."""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            cursor.execute("""
                INSERT OR REPLACE INTO performance_metrics (
                    timestamp, metric_name, metric_value, sheet_name, additional_data
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(),
                metric_name,
                value,
                sheet_name,
                json.dumps(additional_data) if additional_data else None
            ))

            conn.commit()
            conn.close()

        except Exception as e:
            print(f"Failed to record performance metric: {e}")

    def _update_daily_summary(self):
        """Update daily summary with latest data."""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            today = datetime.now().date().isoformat()

            # Calculate today's totals
            cursor.execute("""
                SELECT
                    SUM(rows_processed) as total_processed,
                    SUM(success_count + likely_count) as total_confirmed,
                    SUM(duration_seconds) as total_duration,
                    COUNT(DISTINCT sheet_name) as sheets_processed
                FROM processing_sessions
                WHERE date(timestamp) = ?
            """, (today,))

            result = cursor.fetchone()
            if result and result[0]:
                total_processed, total_confirmed, total_duration, sheets = result

                success_rate = (total_confirmed / total_processed * 100) if total_processed > 0 else 0
                duration_hours = (total_duration / 3600) if total_duration else 0
                processing_speed = (total_processed / duration_hours) if duration_hours > 0 else 0

                cursor.execute("""
                    INSERT OR REPLACE INTO daily_summaries (
                        date, total_processed, total_confirmed, avg_success_rate,
                        total_duration_hours, processing_speed
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    today, total_processed, total_confirmed, success_rate,
                    duration_hours, processing_speed
                ))

            conn.commit()
            conn.close()

        except Exception as e:
            print(f"Failed to update daily summary: {e}")

    def get_trend_summary(self, days: int = 30) -> Dict:
        """Get comprehensive trend summary for the specified period."""
        try:
            conn = sqlite3.connect(str(self.db_path))

            summary = {
                "period_days": days,
                "processing_trends": self._get_processing_trends(conn, days),
                "success_rate_trends": self._get_success_rate_trends(conn, days),
                "performance_trends": self._get_performance_trends(conn, days),
                "enhancement_impact": self._get_enhancement_impact(conn, days),
                "recommendations": [],
                "timestamp": datetime.now().isoformat()
            }

            # Generate recommendations based on trends
            summary["recommendations"] = self._generate_trend_recommendations(summary)

            conn.close()
            return summary

        except Exception as e:
            print(f"Failed to get trend summary: {e}")
            return {"error": str(e)}

    def _get_processing_trends(self, conn: sqlite3.Connection, days: int) -> Dict:
        """Analyze processing volume and speed trends."""
        cursor = conn.cursor()
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

        # Daily processing volumes
        cursor.execute("""
            SELECT date, total_processed, processing_speed
            FROM daily_summaries
            WHERE date >= ?
            ORDER BY date
        """, (cutoff_date[:10],))

        daily_data = cursor.fetchall()

        if not daily_data:
            return {"error": "No processing data available"}

        dates, volumes, speeds = zip(*daily_data)

        trends = {
            "daily_volumes": dict(zip(dates, volumes)),
            "daily_speeds": dict(zip(dates, speeds)),
            "total_volume": sum(volumes),
            "avg_daily_volume": sum(volumes) / len(volumes),
            "avg_processing_speed": statistics.mean([s for s in speeds if s > 0]),
            "volume_trend": self._calculate_trend(list(volumes)),
            "speed_trend": self._calculate_trend([s for s in speeds if s > 0])
        }

        return trends

    def _get_success_rate_trends(self, conn: sqlite3.Connection, days: int) -> Dict:
        """Analyze success rate trends over time."""
        cursor = conn.cursor()
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

        # Success rates by sheet over time
        cursor.execute("""
            SELECT
                sheet_name,
                date(timestamp) as date,
                AVG(CAST(success_count + likely_count AS FLOAT) / NULLIF(rows_processed, 0) * 100) as success_rate
            FROM processing_sessions
            WHERE timestamp >= ?
            GROUP BY sheet_name, date(timestamp)
            ORDER BY date, sheet_name
        """, (cutoff_date,))

        results = cursor.fetchall()

        success_trends = defaultdict(list)
        for sheet, date, rate in results:
            success_trends[sheet].append({"date": date, "rate": rate})

        # Overall trend
        cursor.execute("""
            SELECT date, avg_success_rate
            FROM daily_summaries
            WHERE date >= ?
            ORDER BY date
        """, (cutoff_date[:10],))

        overall_data = cursor.fetchall()
        overall_rates = [rate for _, rate in overall_data if rate is not None]

        trends = {
            "by_sheet": dict(success_trends),
            "overall_trend": self._calculate_trend(overall_rates) if overall_rates else "no_data",
            "current_avg": statistics.mean(overall_rates[-7:]) if len(overall_rates) >= 7 else None,
            "period_avg": statistics.mean(overall_rates) if overall_rates else None,
            "best_performing_sheet": self._get_best_performing_sheet(success_trends),
            "improvement_rate": self._calculate_improvement_rate(overall_rates)
        }

        return trends

    def _get_performance_trends(self, conn: sqlite3.Connection, days: int) -> Dict:
        """Analyze system performance trends."""
        cursor = conn.cursor()
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

        # Get performance metrics
        cursor.execute("""
            SELECT metric_name, timestamp, metric_value
            FROM performance_metrics
            WHERE timestamp >= ?
            ORDER BY metric_name, timestamp
        """, (cutoff_date,))

        metrics_data = defaultdict(list)
        for metric_name, timestamp, value in cursor.fetchall():
            metrics_data[metric_name].append({
                "timestamp": timestamp,
                "value": value
            })

        performance = {}
        for metric_name, data_points in metrics_data.items():
            values = [point["value"] for point in data_points]
            performance[metric_name] = {
                "current": values[-1] if values else None,
                "average": statistics.mean(values) if values else None,
                "trend": self._calculate_trend(values),
                "data_points": len(values)
            }

        return performance

    def _get_enhancement_impact(self, conn: sqlite3.Connection, days: int) -> Dict:
        """Analyze impact of enhancement implementations."""
        cursor = conn.cursor()
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

        # Compare standard vs enhanced processing
        cursor.execute("""
            SELECT
                enhancement_type,
                COUNT(*) as sessions,
                AVG(CAST(success_count + likely_count AS FLOAT) / NULLIF(rows_processed, 0) * 100) as avg_success_rate,
                AVG(rows_processed / NULLIF(duration_seconds, 0) * 3600) as avg_hourly_rate
            FROM processing_sessions
            WHERE timestamp >= ?
            GROUP BY enhancement_type
        """, (cutoff_date,))

        enhancement_data = {}
        for enhancement_type, sessions, success_rate, hourly_rate in cursor.fetchall():
            enhancement_data[enhancement_type] = {
                "sessions": sessions,
                "avg_success_rate": success_rate,
                "avg_hourly_rate": hourly_rate
            }

        # Calculate improvement
        impact = {
            "enhancement_data": enhancement_data,
            "improvement": {},
            "phase1_effectiveness": "Not yet measured"
        }

        if "enhanced" in enhancement_data and "standard" in enhancement_data:
            standard = enhancement_data["standard"]
            enhanced = enhancement_data["enhanced"]

            impact["improvement"] = {
                "success_rate_improvement": enhanced["avg_success_rate"] - standard["avg_success_rate"],
                "speed_improvement": enhanced["avg_hourly_rate"] - standard["avg_hourly_rate"],
                "sessions_compared": f"{enhanced['sessions']} enhanced vs {standard['sessions']} standard"
            }

        return impact

    def _calculate_trend(self, values: List[float]) -> str:
        """Calculate trend direction from a series of values."""
        if len(values) < 2:
            return "insufficient_data"

        # Use linear regression slope to determine trend
        n = len(values)
        x_values = list(range(n))

        x_sum = sum(x_values)
        y_sum = sum(values)
        xy_sum = sum(x * y for x, y in zip(x_values, values))
        x2_sum = sum(x * x for x in x_values)

        slope = (n * xy_sum - x_sum * y_sum) / (n * x2_sum - x_sum * x_sum)

        if slope > 0.1:
            return "improving"
        elif slope < -0.1:
            return "declining"
        else:
            return "stable"

    def _calculate_improvement_rate(self, values: List[float]) -> Optional[float]:
        """Calculate the rate of improvement over time."""
        if len(values) < 2:
            return None

        # Compare first and last values
        initial = statistics.mean(values[:min(3, len(values))])
        recent = statistics.mean(values[-min(3, len(values)):])

        return ((recent - initial) / initial) * 100 if initial > 0 else None

    def _get_best_performing_sheet(self, success_trends: Dict) -> Optional[str]:
        """Identify the best performing sheet."""
        if not success_trends:
            return None

        sheet_averages = {}
        for sheet, data_points in success_trends.items():
            rates = [point["rate"] for point in data_points if point["rate"] is not None]
            if rates:
                sheet_averages[sheet] = statistics.mean(rates)

        return max(sheet_averages.items(), key=lambda x: x[1])[0] if sheet_averages else None

    def _generate_trend_recommendations(self, summary: Dict) -> List[str]:
        """Generate recommendations based on trend analysis."""
        recommendations = []

        # Processing trends
        processing = summary.get("processing_trends", {})
        if processing.get("volume_trend") == "declining":
            recommendations.append("Consider increasing processing capacity - volume trend is declining")
        elif processing.get("speed_trend") == "declining":
            recommendations.append("Investigate performance bottlenecks - processing speed is declining")

        # Success rate trends
        success = summary.get("success_rate_trends", {})
        if success.get("overall_trend") == "declining":
            recommendations.append("Review matching algorithms - success rate trend is declining")
        elif success.get("overall_trend") == "improving":
            recommendations.append("Success rates are improving - consider expanding processing scope")

        # Enhancement impact
        enhancement = summary.get("enhancement_impact", {})
        if "improvement" in enhancement and enhancement["improvement"]:
            improvement = enhancement["improvement"]
            if improvement.get("success_rate_improvement", 0) > 5:
                recommendations.append("Enhanced image analysis is significantly improving results - prioritize deployment")

        # Performance trends
        performance = summary.get("performance_trends", {})
        for metric_name, data in performance.items():
            if data.get("trend") == "declining":
                recommendations.append(f"Monitor {metric_name} - trend is declining")

        return recommendations

    def get_processing_velocity(self, sheet_name: str = None, days: int = 7) -> Dict:
        """Get processing velocity analysis for optimization."""
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()

            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

            where_clause = "WHERE timestamp >= ?"
            params = [cutoff_date]

            if sheet_name:
                where_clause += " AND sheet_name = ?"
                params.append(sheet_name)

            cursor.execute(f"""
                SELECT
                    timestamp,
                    sheet_name,
                    rows_processed,
                    duration_seconds,
                    enhancement_type
                FROM processing_sessions
                {where_clause}
                ORDER BY timestamp
            """, params)

            sessions = cursor.fetchall()
            conn.close()

            if not sessions:
                return {"error": "No session data available"}

            # Calculate velocity metrics
            velocity = {
                "total_sessions": len(sessions),
                "total_rows": sum(session[2] for session in sessions),
                "total_hours": sum(session[3] for session in sessions if session[3]) / 3600,
                "avg_rows_per_hour": 0,
                "peak_performance": 0,
                "consistency_score": 0,
                "enhancement_impact": {}
            }

            if velocity["total_hours"] > 0:
                velocity["avg_rows_per_hour"] = velocity["total_rows"] / velocity["total_hours"]

            # Find peak performance
            hourly_rates = []
            for session in sessions:
                if session[3] and session[3] > 0:
                    rate = session[2] / (session[3] / 3600)
                    hourly_rates.append(rate)

            if hourly_rates:
                velocity["peak_performance"] = max(hourly_rates)
                velocity["consistency_score"] = (statistics.mean(hourly_rates) / max(hourly_rates)) * 100

            # Enhancement impact analysis
            standard_rates = []
            enhanced_rates = []

            for session in sessions:
                if session[3] and session[3] > 0:
                    rate = session[2] / (session[3] / 3600)
                    if session[4] == "enhanced":
                        enhanced_rates.append(rate)
                    else:
                        standard_rates.append(rate)

            if standard_rates and enhanced_rates:
                velocity["enhancement_impact"] = {
                    "standard_avg": statistics.mean(standard_rates),
                    "enhanced_avg": statistics.mean(enhanced_rates),
                    "improvement_factor": statistics.mean(enhanced_rates) / statistics.mean(standard_rates)
                }

            return velocity

        except Exception as e:
            return {"error": str(e)}

    def export_trends(self, filepath: str, days: int = 30) -> bool:
        """Export trend analysis to file."""
        try:
            trends = self.get_trend_summary(days)
            with open(filepath, 'w') as f:
                json.dump(trends, f, indent=2, default=str)
            return True
        except Exception as e:
            print(f"Failed to export trends: {e}")
            return False

    def get_historical_comparison(self, sheet_name: str, days1: int = 7, days2: int = 14) -> Dict:
        """Compare performance between two time periods."""
        try:
            # Get recent period
            recent_summary = self.get_trend_summary(days1)
            # Get comparison period
            older_summary = self.get_trend_summary(days2)

            comparison = {
                "recent_period": f"Last {days1} days",
                "comparison_period": f"Days {days1}-{days2}",
                "improvements": [],
                "regressions": [],
                "stable_metrics": []
            }

            # Compare key metrics
            recent_processing = recent_summary.get("processing_trends", {})
            older_processing = older_summary.get("processing_trends", {})

            if "avg_daily_volume" in recent_processing and "avg_daily_volume" in older_processing:
                volume_change = recent_processing["avg_daily_volume"] - older_processing["avg_daily_volume"]
                if volume_change > 10:
                    comparison["improvements"].append(f"Daily processing volume increased by {volume_change:.0f} rows")
                elif volume_change < -10:
                    comparison["regressions"].append(f"Daily processing volume decreased by {abs(volume_change):.0f} rows")

            return comparison

        except Exception as e:
            return {"error": str(e)}