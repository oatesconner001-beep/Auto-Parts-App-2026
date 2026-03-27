"""
Enhanced Analytics Package for Parts Agent

Provides comprehensive analytics, reporting, and data intelligence capabilities
for the automated parts matching system.

Modules:
- stats_engine: Core statistics calculation and analysis
- trend_analyzer: Historical trend analysis and forecasting
- performance_metrics: Processing performance tracking
- data_quality: Data quality analysis and validation
- dashboard: Interactive analytics dashboard
- chart_generator: Chart and graph generation
- report_generator: Automated report creation
- export_manager: Export analytics to various formats
"""

from .stats_engine import StatsEngine
from .trend_analyzer import TrendAnalyzer
from .performance_metrics import PerformanceTracker
from .data_quality import DataQualityAnalyzer

__version__ = "1.0.0"
__author__ = "Parts Agent Enhanced Analytics System"

# Main analytics interface
class Analytics:
    """
    Main analytics interface that provides access to all analytics capabilities.
    """

    def __init__(self, excel_path: str = None):
        self.excel_path = excel_path
        self.stats_engine = StatsEngine(excel_path)
        self.trend_analyzer = TrendAnalyzer(excel_path)
        self.performance_tracker = PerformanceTracker()
        self.quality_analyzer = DataQualityAnalyzer(excel_path)

    def get_comprehensive_report(self) -> dict:
        """Get comprehensive analytics report combining all modules."""
        return {
            "overview": self.stats_engine.get_summary_stats(),
            "trends": self.trend_analyzer.get_trend_summary(),
            "performance": self.performance_tracker.get_performance_summary(),
            "quality": self.quality_analyzer.get_quality_summary(),
            "timestamp": self.stats_engine.get_timestamp()
        }

# Export main classes for easy import
__all__ = [
    "Analytics",
    "StatsEngine",
    "TrendAnalyzer",
    "PerformanceTracker",
    "DataQualityAnalyzer"
]