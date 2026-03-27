"""
Interactive Analytics Dashboard for Parts Agent

Provides comprehensive analytics visualization and reporting capabilities.
Integrates with the existing GUI to display real-time analytics and insights.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import seaborn as sns
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import threading
import time
from pathlib import Path

from .stats_engine import StatsEngine
from .trend_analyzer import TrendAnalyzer
from .performance_metrics import PerformanceTracker
from .data_quality import DataQualityAnalyzer

# Configure matplotlib for better appearance
plt.style.use('default')
sns.set_palette("husl")

class AnalyticsDashboard:
    """
    Interactive analytics dashboard with real-time charts and insights.

    Features:
    - Real-time performance monitoring
    - Interactive charts and graphs
    - Quality metrics visualization
    - Trend analysis displays
    - Export capabilities
    """

    def __init__(self, parent_window: tk.Widget, excel_path: str = None):
        self.parent = parent_window
        self.excel_path = excel_path

        # Initialize analytics engines
        self.stats_engine = StatsEngine(excel_path)
        self.trend_analyzer = TrendAnalyzer(excel_path)
        self.performance_tracker = PerformanceTracker()
        self.quality_analyzer = DataQualityAnalyzer(excel_path)

        # Dashboard state
        self.dashboard_window = None
        self.charts = {}
        self.refresh_thread = None
        self.auto_refresh_enabled = tk.BooleanVar(value=True)
        self.refresh_interval = 30  # seconds

        # Chart data cache
        self._chart_data_cache = {}
        self._last_refresh = None

    def show_dashboard(self):
        """Show the analytics dashboard window."""
        if self.dashboard_window and self.dashboard_window.winfo_exists():
            self.dashboard_window.lift()
            return

        self.dashboard_window = tk.Toplevel(self.parent)
        self.dashboard_window.title("Parts Agent - Analytics Dashboard")
        self.dashboard_window.geometry("1400x900")
        self.dashboard_window.resizable(True, True)

        # Configure window
        self._setup_dashboard_layout()

        # Initial data load
        self._refresh_all_charts()

        # Start auto-refresh if enabled
        if self.auto_refresh_enabled.get():
            self._start_auto_refresh()

        # Handle window close
        self.dashboard_window.protocol("WM_DELETE_WINDOW", self._on_dashboard_close)

    def _setup_dashboard_layout(self):
        """Setup the dashboard layout with tabs and charts."""
        # Create main notebook for tabs
        self.main_notebook = ttk.Notebook(self.dashboard_window)
        self.main_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Create tabs
        self._create_overview_tab()
        self._create_performance_tab()
        self._create_quality_tab()
        self._create_trends_tab()
        self._create_sheets_comparison_tab()

        # Create control panel at bottom
        self._create_control_panel()

    def _create_overview_tab(self):
        """Create overview tab with key metrics."""
        overview_frame = ttk.Frame(self.main_notebook)
        self.main_notebook.add(overview_frame, text="Overview")

        # Create grid layout
        overview_frame.columnconfigure(0, weight=1)
        overview_frame.columnconfigure(1, weight=1)
        overview_frame.rowconfigure(1, weight=1)

        # Key metrics panel
        metrics_frame = ttk.LabelFrame(overview_frame, text="Key Metrics")
        metrics_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=5, pady=5)

        self.metrics_text = tk.Text(metrics_frame, height=6, wrap=tk.WORD, state="disabled")
        self.metrics_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Processing status chart
        status_frame = ttk.LabelFrame(overview_frame, text="Processing Status")
        status_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

        self.status_figure = Figure(figsize=(6, 4), dpi=100)
        self.status_canvas = FigureCanvasTkAgg(self.status_figure, status_frame)
        self.status_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Success rate distribution
        success_frame = ttk.LabelFrame(overview_frame, text="Success Rate by Sheet")
        success_frame.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)

        self.success_figure = Figure(figsize=(6, 4), dpi=100)
        self.success_canvas = FigureCanvasTkAgg(self.success_figure, success_frame)
        self.success_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def _create_performance_tab(self):
        """Create performance monitoring tab."""
        performance_frame = ttk.Frame(self.main_notebook)
        self.main_notebook.add(performance_frame, text="Performance")

        # Configure grid
        performance_frame.columnconfigure(0, weight=1)
        performance_frame.columnconfigure(1, weight=1)
        performance_frame.rowconfigure(0, weight=1)
        performance_frame.rowconfigure(1, weight=1)

        # Processing speed chart
        speed_frame = ttk.LabelFrame(performance_frame, text="Processing Speed Over Time")
        speed_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        self.speed_figure = Figure(figsize=(6, 4), dpi=100)
        self.speed_canvas = FigureCanvasTkAgg(self.speed_figure, speed_frame)
        self.speed_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # System resources chart
        resources_frame = ttk.LabelFrame(performance_frame, text="System Resources")
        resources_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

        self.resources_figure = Figure(figsize=(6, 4), dpi=100)
        self.resources_canvas = FigureCanvasTkAgg(self.resources_figure, resources_frame)
        self.resources_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Network performance
        network_frame = ttk.LabelFrame(performance_frame, text="Network Performance")
        network_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

        self.network_figure = Figure(figsize=(6, 4), dpi=100)
        self.network_canvas = FigureCanvasTkAgg(self.network_figure, network_frame)
        self.network_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Performance summary
        perf_summary_frame = ttk.LabelFrame(performance_frame, text="Performance Summary")
        perf_summary_frame.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)

        self.perf_summary_text = tk.Text(perf_summary_frame, wrap=tk.WORD, state="disabled")
        self.perf_summary_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def _create_quality_tab(self):
        """Create data quality analysis tab."""
        quality_frame = ttk.Frame(self.main_notebook)
        self.main_notebook.add(quality_frame, text="Data Quality")

        # Configure grid
        quality_frame.columnconfigure(0, weight=1)
        quality_frame.columnconfigure(1, weight=1)
        quality_frame.rowconfigure(0, weight=1)
        quality_frame.rowconfigure(1, weight=1)

        # Quality score chart
        quality_score_frame = ttk.LabelFrame(quality_frame, text="Overall Quality Score")
        quality_score_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        self.quality_score_figure = Figure(figsize=(6, 4), dpi=100)
        self.quality_score_canvas = FigureCanvasTkAgg(self.quality_score_figure, quality_score_frame)
        self.quality_score_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Confidence distribution
        confidence_frame = ttk.LabelFrame(quality_frame, text="Confidence Distribution")
        confidence_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

        self.confidence_figure = Figure(figsize=(6, 4), dpi=100)
        self.confidence_canvas = FigureCanvasTkAgg(self.confidence_figure, confidence_frame)
        self.confidence_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Anomalies and issues
        anomalies_frame = ttk.LabelFrame(quality_frame, text="Data Issues")
        anomalies_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

        self.anomalies_text = tk.Text(anomalies_frame, wrap=tk.WORD, state="disabled")
        self.anomalies_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Quality recommendations
        quality_rec_frame = ttk.LabelFrame(quality_frame, text="Quality Recommendations")
        quality_rec_frame.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)

        self.quality_rec_text = tk.Text(quality_rec_frame, wrap=tk.WORD, state="disabled")
        self.quality_rec_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def _create_trends_tab(self):
        """Create trends analysis tab."""
        trends_frame = ttk.Frame(self.main_notebook)
        self.main_notebook.add(trends_frame, text="Trends")

        # Configure grid
        trends_frame.columnconfigure(0, weight=1)
        trends_frame.columnconfigure(1, weight=1)
        trends_frame.rowconfigure(0, weight=1)
        trends_frame.rowconfigure(1, weight=1)

        # Success rate trends
        success_trend_frame = ttk.LabelFrame(trends_frame, text="Success Rate Trends")
        success_trend_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        self.success_trend_figure = Figure(figsize=(6, 4), dpi=100)
        self.success_trend_canvas = FigureCanvasTkAgg(self.success_trend_figure, success_trend_frame)
        self.success_trend_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Processing volume trends
        volume_trend_frame = ttk.LabelFrame(trends_frame, text="Processing Volume Trends")
        volume_trend_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)

        self.volume_trend_figure = Figure(figsize=(6, 4), dpi=100)
        self.volume_trend_canvas = FigureCanvasTkAgg(self.volume_trend_figure, volume_trend_frame)
        self.volume_trend_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Enhancement impact
        enhancement_frame = ttk.LabelFrame(trends_frame, text="Enhancement Impact Analysis")
        enhancement_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

        self.enhancement_figure = Figure(figsize=(6, 4), dpi=100)
        self.enhancement_canvas = FigureCanvasTkAgg(self.enhancement_figure, enhancement_frame)
        self.enhancement_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Trend insights
        trend_insights_frame = ttk.LabelFrame(trends_frame, text="Trend Insights")
        trend_insights_frame.grid(row=1, column=1, sticky="nsew", padx=5, pady=5)

        self.trend_insights_text = tk.Text(trend_insights_frame, wrap=tk.WORD, state="disabled")
        self.trend_insights_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def _create_sheets_comparison_tab(self):
        """Create sheet comparison tab."""
        comparison_frame = ttk.Frame(self.main_notebook)
        self.main_notebook.add(comparison_frame, text="Sheet Comparison")

        # Configure grid
        comparison_frame.columnconfigure(0, weight=1)
        comparison_frame.rowconfigure(0, weight=1)
        comparison_frame.rowconfigure(1, weight=1)

        # Comparison chart
        comparison_chart_frame = ttk.LabelFrame(comparison_frame, text="Sheet Performance Comparison")
        comparison_chart_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        self.comparison_figure = Figure(figsize=(12, 6), dpi=100)
        self.comparison_canvas = FigureCanvasTkAgg(self.comparison_figure, comparison_chart_frame)
        self.comparison_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Detailed comparison table
        table_frame = ttk.LabelFrame(comparison_frame, text="Detailed Comparison")
        table_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

        # Create treeview for detailed comparison
        columns = ("Sheet", "Total Rows", "Processed", "Success Rate", "Avg Confidence", "Quality Score")
        self.comparison_tree = ttk.Treeview(table_frame, columns=columns, show="headings")

        for col in columns:
            self.comparison_tree.heading(col, text=col)
            self.comparison_tree.column(col, width=100, anchor=tk.CENTER)

        # Scrollbar for treeview
        comparison_scroll = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.comparison_tree.yview)
        self.comparison_tree.configure(yscrollcommand=comparison_scroll.set)

        self.comparison_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5,0), pady=5)
        comparison_scroll.pack(side=tk.RIGHT, fill=tk.Y, pady=5, padx=(0,5))

    def _create_control_panel(self):
        """Create control panel at bottom of dashboard."""
        control_frame = ttk.Frame(self.dashboard_window)
        control_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)

        # Auto-refresh controls
        refresh_frame = ttk.LabelFrame(control_frame, text="Refresh Controls")
        refresh_frame.pack(side=tk.LEFT, padx=5)

        ttk.Checkbutton(
            refresh_frame, text="Auto-refresh",
            variable=self.auto_refresh_enabled,
            command=self._toggle_auto_refresh
        ).pack(side=tk.LEFT, padx=5, pady=5)

        ttk.Button(
            refresh_frame, text="Refresh Now",
            command=self._refresh_all_charts
        ).pack(side=tk.LEFT, padx=5, pady=5)

        # Export controls
        export_frame = ttk.LabelFrame(control_frame, text="Export")
        export_frame.pack(side=tk.LEFT, padx=5)

        ttk.Button(
            export_frame, text="Export Analytics",
            command=self._export_analytics_report
        ).pack(side=tk.LEFT, padx=5, pady=5)

        ttk.Button(
            export_frame, text="Export Charts",
            command=self._export_charts
        ).pack(side=tk.LEFT, padx=5, pady=5)

        # Status display
        self.status_label = ttk.Label(control_frame, text="Ready")
        self.status_label.pack(side=tk.RIGHT, padx=5, pady=5)

    def _refresh_all_charts(self):
        """Refresh all charts and data displays."""
        self._update_status("Refreshing analytics data...")

        try:
            # Load fresh data
            stats_data = self.stats_engine.get_summary_stats()
            quality_data = self.quality_analyzer.get_quality_summary()
            performance_data = self.performance_tracker.get_performance_summary()
            trend_data = self.trend_analyzer.get_trend_summary()

            # Update all charts
            self._update_overview_tab(stats_data)
            self._update_performance_tab(performance_data)
            self._update_quality_tab(quality_data)
            self._update_trends_tab(trend_data)
            self._update_comparison_tab(stats_data)

            self._last_refresh = datetime.now()
            self._update_status(f"Last refreshed: {self._last_refresh.strftime('%H:%M:%S')}")

        except Exception as e:
            self._update_status(f"Error refreshing: {str(e)}")
            messagebox.showerror("Refresh Error", f"Failed to refresh analytics data:\n{str(e)}")

    def _update_overview_tab(self, stats_data: Dict):
        """Update overview tab with latest statistics."""
        # Update key metrics
        overview = stats_data.get("overview", {})
        metrics_text = f"""
PROCESSING OVERVIEW
Total Rows: {overview.get('total_rows', 0):,}
Processed: {overview.get('processed_rows', 0):,} ({overview.get('processing_completion', 0):.1f}%)
Success Rate: {overview.get('success_rate', 0):.1f}%

MATCH RESULTS
YES: {overview.get('YES', 0):,}
LIKELY: {overview.get('LIKELY', 0):,}
UNCERTAIN: {overview.get('UNCERTAIN', 0):,}
NO: {overview.get('NO', 0):,}

READY FOR ENHANCEMENT
Enhanced Analysis Ready: {overview.get('needs_review', 0):,} UNCERTAIN rows
Expected Additional Matches: ~{int(overview.get('needs_review', 0) * 1.0)} (100% rate)
        """.strip()

        self._update_text_widget(self.metrics_text, metrics_text)

        # Update processing status chart
        self.status_figure.clear()
        ax = self.status_figure.add_subplot(111)

        if overview.get('processed_rows', 0) > 0:
            labels = ['YES', 'LIKELY', 'UNCERTAIN', 'NO']
            sizes = [overview.get(label, 0) for label in labels]
            colors = ['#2E8B57', '#90EE90', '#FFD700', '#FF6347']

            wedges, texts, autotexts = ax.pie(sizes, labels=labels, colors=colors,
                                            autopct='%1.1f%%', startangle=90)
            ax.set_title('Match Result Distribution')
        else:
            ax.text(0.5, 0.5, 'No processed data\navailable', ha='center', va='center',
                   transform=ax.transAxes, fontsize=14)

        self.status_canvas.draw()

        # Update success rate by sheet chart
        self.success_figure.clear()
        ax = self.success_figure.add_subplot(111)

        sheet_data = stats_data.get("by_sheet", {})
        if sheet_data:
            sheets = list(sheet_data.keys())
            success_rates = [sheet_data[sheet].get('success_rate', 0) for sheet in sheets]

            bars = ax.bar(sheets, success_rates, color='skyblue', alpha=0.7)
            ax.set_title('Success Rate by Sheet')
            ax.set_ylabel('Success Rate (%)')
            ax.set_ylim(0, 100)

            # Rotate x-axis labels for better readability
            ax.tick_params(axis='x', rotation=45)

            # Add value labels on bars
            for bar, rate in zip(bars, success_rates):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + 1,
                       f'{rate:.1f}%', ha='center', va='bottom', fontsize=8)

        else:
            ax.text(0.5, 0.5, 'No sheet data\navailable', ha='center', va='center',
                   transform=ax.transAxes, fontsize=14)

        self.success_figure.tight_layout()
        self.success_canvas.draw()

    def _update_performance_tab(self, performance_data: Dict):
        """Update performance tab with latest data."""
        # Update performance summary
        current_status = performance_data.get("current_status", {})
        system_perf = performance_data.get("system_performance", {})
        processing_perf = performance_data.get("processing_performance", {})
        network_perf = performance_data.get("network_performance", {})

        perf_text = f"""
CURRENT SESSION
Status: {current_status.get('status', 'idle').upper()}
Current Speed: {current_status.get('current_speed', 0):.1f} rows/second

SYSTEM PERFORMANCE
CPU Usage: {system_perf.get('current_cpu', 0):.1f}%
Memory Usage: {system_perf.get('current_memory', 0):.1f}%
Chrome Processes: {system_perf.get('chrome_processes', 0)}
Chrome Memory: {system_perf.get('chrome_memory_mb', 0):.0f} MB

PROCESSING PERFORMANCE
Average Speed: {processing_perf.get('avg_speed', 0):.1f} rows/second
Peak Speed: {processing_perf.get('peak_speed', 0):.1f} rows/second

NETWORK PERFORMANCE
Avg Request Time: {network_perf.get('avg_request_time', 0):.1f} seconds
Slow Requests: {network_perf.get('slow_requests', 0)}
        """.strip()

        self._update_text_widget(self.perf_summary_text, perf_text)

        # TODO: Add actual performance charts with historical data
        # For now, create placeholder charts

        # Processing speed chart
        self.speed_figure.clear()
        ax = self.speed_figure.add_subplot(111)
        ax.text(0.5, 0.5, 'Processing Speed\nChart\n(Historical data)',
               ha='center', va='center', transform=ax.transAxes, fontsize=12)
        ax.set_title('Processing Speed Over Time')
        self.speed_canvas.draw()

        # System resources chart
        self.resources_figure.clear()
        ax = self.resources_figure.add_subplot(111)
        if system_perf:
            resources = ['CPU', 'Memory']
            usage = [system_perf.get('current_cpu', 0), system_perf.get('current_memory', 0)]
            colors = ['red' if x > 80 else 'orange' if x > 60 else 'green' for x in usage]

            bars = ax.bar(resources, usage, color=colors, alpha=0.7)
            ax.set_title('Current System Resource Usage')
            ax.set_ylabel('Usage (%)')
            ax.set_ylim(0, 100)

            for bar, value in zip(bars, usage):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + 2,
                       f'{value:.1f}%', ha='center', va='bottom')
        else:
            ax.text(0.5, 0.5, 'No system data\navailable', ha='center', va='center',
                   transform=ax.transAxes, fontsize=14)

        self.resources_canvas.draw()

        # Network performance chart
        self.network_figure.clear()
        ax = self.network_figure.add_subplot(111)
        ax.text(0.5, 0.5, 'Network Performance\nChart\n(Request timing)',
               ha='center', va='center', transform=ax.transAxes, fontsize=12)
        ax.set_title('Network Request Performance')
        self.network_canvas.draw()

    def _update_quality_tab(self, quality_data: Dict):
        """Update data quality tab."""
        overall_quality = quality_data.get("overall_quality", {})
        confidence_reliability = quality_data.get("confidence_reliability", {})
        anomalies = quality_data.get("anomaly_detection", {})
        recommendations = quality_data.get("recommendations", [])

        # Update quality score chart
        self.quality_score_figure.clear()
        ax = self.quality_score_figure.add_subplot(111)

        components = overall_quality.get("component_scores", {})
        if components:
            comp_names = list(components.keys())
            comp_scores = list(components.values())

            bars = ax.bar(comp_names, comp_scores, color='lightblue', alpha=0.7)
            ax.set_title(f'Quality Components (Overall: {overall_quality.get("overall_score", 0):.1f})')
            ax.set_ylabel('Score')
            ax.set_ylim(0, 100)

            # Add grade indicator
            grade = overall_quality.get("grade", "N/A")
            ax.text(0.02, 0.98, f'Grade: {grade}', transform=ax.transAxes,
                   bbox=dict(boxstyle="round,pad=0.3", facecolor="lightgreen"),
                   fontsize=12, verticalalignment='top')

            ax.tick_params(axis='x', rotation=45)

        self.quality_score_canvas.draw()

        # Update confidence distribution
        self.confidence_figure.clear()
        ax = self.confidence_figure.add_subplot(111)

        dist_analysis = confidence_reliability.get("distribution_analysis", {})
        if dist_analysis and "buckets" in dist_analysis:
            buckets = dist_analysis["buckets"]
            labels = list(buckets.keys())
            values = list(buckets.values())

            bars = ax.bar(labels, values, color='orange', alpha=0.7)
            ax.set_title('Confidence Score Distribution')
            ax.set_ylabel('Count')
            ax.tick_params(axis='x', rotation=45)

        self.confidence_canvas.draw()

        # Update anomalies text
        anomaly_text = "DATA ANOMALIES DETECTED:\n\n"
        total_anomalies = 0
        for anomaly_type, anomaly_list in anomalies.items():
            if isinstance(anomaly_list, list) and anomaly_list:
                total_anomalies += len(anomaly_list)
                anomaly_text += f"{anomaly_type.replace('_', ' ').title()}: {len(anomaly_list)}\n"

        if total_anomalies == 0:
            anomaly_text = "No significant data anomalies detected.\nData quality appears good."

        self._update_text_widget(self.anomalies_text, anomaly_text)

        # Update quality recommendations
        rec_text = "QUALITY IMPROVEMENT RECOMMENDATIONS:\n\n"
        for i, rec in enumerate(recommendations[:10], 1):  # Limit to 10 recommendations
            rec_text += f"{i}. {rec}\n\n"

        if not recommendations:
            rec_text = "No specific quality recommendations at this time.\nData quality is acceptable."

        self._update_text_widget(self.quality_rec_text, rec_text)

    def _update_trends_tab(self, trend_data: Dict):
        """Update trends analysis tab."""
        # Update trend insights text
        processing_trends = trend_data.get("processing_trends", {})
        success_trends = trend_data.get("success_rate_trends", {})
        enhancement_impact = trend_data.get("enhancement_impact", {})
        recommendations = trend_data.get("recommendations", [])

        insights_text = "TREND INSIGHTS:\n\n"

        if processing_trends:
            insights_text += f"Processing Volume Trend: {processing_trends.get('volume_trend', 'N/A').replace('_', ' ').title()}\n"
            insights_text += f"Processing Speed Trend: {processing_trends.get('speed_trend', 'N/A').replace('_', ' ').title()}\n\n"

        if success_trends:
            insights_text += f"Success Rate Trend: {success_trends.get('overall_trend', 'N/A').replace('_', ' ').title()}\n"
            best_sheet = success_trends.get("best_performing_sheet")
            if best_sheet:
                insights_text += f"Best Performing Sheet: {best_sheet}\n\n"

        if enhancement_impact.get("improvement"):
            improvement = enhancement_impact["improvement"]
            insights_text += "ENHANCEMENT IMPACT:\n"
            insights_text += f"Success Rate Improvement: +{improvement.get('success_rate_improvement', 0):.1f}%\n"
            insights_text += f"Speed Improvement: +{improvement.get('speed_improvement', 0):.1f} rows/hour\n\n"

        if recommendations:
            insights_text += "RECOMMENDATIONS:\n"
            for rec in recommendations[:5]:
                insights_text += f"• {rec}\n"

        self._update_text_widget(self.trend_insights_text, insights_text)

        # Create placeholder trend charts
        # TODO: Implement actual trend charts with historical data

        self.success_trend_figure.clear()
        ax = self.success_trend_figure.add_subplot(111)
        ax.text(0.5, 0.5, 'Success Rate\nTrend Chart', ha='center', va='center',
               transform=ax.transAxes, fontsize=12)
        ax.set_title('Success Rate Trends')
        self.success_trend_canvas.draw()

        self.volume_trend_figure.clear()
        ax = self.volume_trend_figure.add_subplot(111)
        ax.text(0.5, 0.5, 'Processing Volume\nTrend Chart', ha='center', va='center',
               transform=ax.transAxes, fontsize=12)
        ax.set_title('Processing Volume Trends')
        self.volume_trend_canvas.draw()

        self.enhancement_figure.clear()
        ax = self.enhancement_figure.add_subplot(111)
        ax.text(0.5, 0.5, 'Enhancement Impact\nAnalysis Chart', ha='center', va='center',
               transform=ax.transAxes, fontsize=12)
        ax.set_title('Enhancement Impact Analysis')
        self.enhancement_canvas.draw()

    def _update_comparison_tab(self, stats_data: Dict):
        """Update sheet comparison tab."""
        sheet_data = stats_data.get("by_sheet", {})

        # Clear existing data in tree
        for item in self.comparison_tree.get_children():
            self.comparison_tree.delete(item)

        # Populate comparison tree
        for sheet_name, data in sheet_data.items():
            self.comparison_tree.insert("", tk.END, values=(
                sheet_name,
                f"{data.get('total_rows', 0):,}",
                f"{data.get('processed', 0):,}",
                f"{data.get('success_rate', 0):.1f}%",
                f"{data.get('avg_confidence', 0):.0f}",
                "B+"  # TODO: Calculate actual quality score
            ))

        # Update comparison chart
        self.comparison_figure.clear()
        ax = self.comparison_figure.add_subplot(111)

        if sheet_data:
            sheets = list(sheet_data.keys())
            processed_counts = [sheet_data[sheet].get('processed', 0) for sheet in sheets]
            success_rates = [sheet_data[sheet].get('success_rate', 0) for sheet in sheets]

            # Create bar chart comparing processing volumes
            x = range(len(sheets))
            width = 0.35

            bars1 = ax.bar([i - width/2 for i in x], processed_counts, width,
                          label='Processed Rows', color='lightblue', alpha=0.7)

            # Create second y-axis for success rates
            ax2 = ax.twinx()
            bars2 = ax2.bar([i + width/2 for i in x], success_rates, width,
                           label='Success Rate (%)', color='lightgreen', alpha=0.7)

            ax.set_xlabel('Sheets')
            ax.set_ylabel('Processed Rows')
            ax2.set_ylabel('Success Rate (%)')
            ax.set_title('Sheet Comparison: Processing Volume vs Success Rate')
            ax.set_xticks(x)
            ax.set_xticklabels(sheets, rotation=45)

            # Add legends
            ax.legend(loc='upper left')
            ax2.legend(loc='upper right')

        self.comparison_figure.tight_layout()
        self.comparison_canvas.draw()

    def _update_text_widget(self, widget: tk.Text, text: str):
        """Update text widget content."""
        widget.config(state="normal")
        widget.delete(1.0, tk.END)
        widget.insert(1.0, text)
        widget.config(state="disabled")

    def _update_status(self, message: str):
        """Update status label."""
        self.status_label.config(text=message)

    def _toggle_auto_refresh(self):
        """Toggle auto-refresh functionality."""
        if self.auto_refresh_enabled.get():
            self._start_auto_refresh()
        else:
            self._stop_auto_refresh()

    def _start_auto_refresh(self):
        """Start auto-refresh thread."""
        if self.refresh_thread and self.refresh_thread.is_alive():
            return

        self.refresh_thread = threading.Thread(target=self._auto_refresh_loop, daemon=True)
        self.refresh_thread.start()

    def _stop_auto_refresh(self):
        """Stop auto-refresh thread."""
        self.auto_refresh_enabled.set(False)

    def _auto_refresh_loop(self):
        """Auto-refresh loop running in background thread."""
        while self.auto_refresh_enabled.get() and self.dashboard_window and self.dashboard_window.winfo_exists():
            time.sleep(self.refresh_interval)
            if self.auto_refresh_enabled.get():
                # Schedule refresh in main thread
                if self.dashboard_window and self.dashboard_window.winfo_exists():
                    self.dashboard_window.after(0, self._refresh_all_charts)

    def _export_analytics_report(self):
        """Export comprehensive analytics report."""
        try:
            export_dir = Path(__file__).parent.parent.parent / "analytics_exports"
            export_dir.mkdir(exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Export stats
            stats_file = export_dir / f"analytics_report_{timestamp}.json"
            self.stats_engine.export_stats(str(stats_file))

            # Export quality report
            quality_file = export_dir / f"quality_report_{timestamp}.json"
            self.quality_analyzer.export_quality_report(str(quality_file))

            # Export performance report
            perf_file = export_dir / f"performance_report_{timestamp}.json"
            self.performance_tracker.export_performance_report(str(perf_file))

            messagebox.showinfo("Export Complete",
                               f"Analytics reports exported to:\n{export_dir}\n\n"
                               f"Files created:\n"
                               f"• analytics_report_{timestamp}.json\n"
                               f"• quality_report_{timestamp}.json\n"
                               f"• performance_report_{timestamp}.json")

        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export reports:\n{str(e)}")

    def _export_charts(self):
        """Export all charts as images."""
        try:
            export_dir = Path(__file__).parent.parent.parent / "analytics_exports" / "charts"
            export_dir.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Export all figures
            chart_files = []
            charts_to_export = [
                (self.status_figure, "processing_status"),
                (self.success_figure, "success_rates"),
                (self.speed_figure, "processing_speed"),
                (self.resources_figure, "system_resources"),
                (self.quality_score_figure, "quality_scores"),
                (self.confidence_figure, "confidence_distribution"),
                (self.comparison_figure, "sheet_comparison")
            ]

            for figure, name in charts_to_export:
                filename = f"{name}_{timestamp}.png"
                filepath = export_dir / filename
                figure.savefig(str(filepath), dpi=300, bbox_inches='tight')
                chart_files.append(filename)

            messagebox.showinfo("Charts Exported",
                               f"Charts exported to:\n{export_dir}\n\n"
                               f"Files created:\n" + "\n".join(f"• {f}" for f in chart_files))

        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export charts:\n{str(e)}")

    def _on_dashboard_close(self):
        """Handle dashboard window close."""
        self._stop_auto_refresh()
        if self.dashboard_window:
            self.dashboard_window.destroy()
            self.dashboard_window = None