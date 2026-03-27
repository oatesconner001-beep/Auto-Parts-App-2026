"""
Chart Generator for Parts Agent Analytics

Generates professional charts and visualizations for analytics data.
Supports various chart types optimized for parts matching analytics.
"""

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import json

# Configure style
plt.style.use('default')
sns.set_palette("husl")
plt.rcParams['figure.facecolor'] = 'white'
plt.rcParams['axes.facecolor'] = 'white'

class ChartGenerator:
    """
    Professional chart generation for analytics data.

    Features:
    - Processing status visualizations
    - Performance trend charts
    - Quality metrics displays
    - Comparison charts
    - Export capabilities
    """

    def __init__(self):
        self.chart_config = {
            "style": "whitegrid",
            "palette": "husl",
            "figure_size": (10, 6),
            "dpi": 300,
            "font_size": 10
        }

        # Color schemes for different chart types
        self.color_schemes = {
            "match_results": {
                "YES": "#2E8B57",      # Sea Green
                "LIKELY": "#90EE90",   # Light Green
                "UNCERTAIN": "#FFD700", # Gold
                "NO": "#FF6347"        # Tomato
            },
            "performance": {
                "excellent": "#2E8B57",
                "good": "#90EE90",
                "fair": "#FFD700",
                "poor": "#FF6347"
            },
            "sheets": ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"]
        }

    def create_processing_status_chart(self, stats_data: Dict, save_path: str = None) -> plt.Figure:
        """Create processing status pie chart."""
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=self.chart_config["figure_size"])

        overview = stats_data.get("overview", {})

        # Overall processing status
        if overview.get('total_rows', 0) > 0:
            processed = overview.get('processed_rows', 0)
            unprocessed = overview.get('total_rows', 0) - processed

            sizes = [processed, unprocessed]
            labels = ['Processed', 'Unprocessed']
            colors = ['lightgreen', 'lightcoral']

            wedges, texts, autotexts = ax1.pie(sizes, labels=labels, colors=colors,
                                             autopct='%1.1f%%', startangle=90)
            ax1.set_title(f'Processing Status\nTotal: {overview.get("total_rows", 0):,} rows')

        # Match results breakdown
        if overview.get('processed_rows', 0) > 0:
            labels = ['YES', 'LIKELY', 'UNCERTAIN', 'NO']
            sizes = [overview.get(label, 0) for label in labels]
            colors = [self.color_schemes["match_results"][label] for label in labels]

            wedges, texts, autotexts = ax2.pie(sizes, labels=labels, colors=colors,
                                             autopct='%1.1f%%', startangle=90)
            ax2.set_title('Match Results Distribution')

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=self.chart_config["dpi"], bbox_inches='tight')

        return fig

    def create_sheet_comparison_chart(self, stats_data: Dict, save_path: str = None) -> plt.Figure:
        """Create sheet comparison bar chart."""
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10))

        sheet_data = stats_data.get("by_sheet", {})
        if not sheet_data:
            fig.text(0.5, 0.5, 'No sheet data available', ha='center', va='center', fontsize=16)
            return fig

        sheets = list(sheet_data.keys())
        colors = self.color_schemes["sheets"][:len(sheets)]

        # Processing completion comparison
        completion_rates = [sheet_data[sheet].get('processed', 0) / sheet_data[sheet].get('total_rows', 1) * 100
                           for sheet in sheets]

        bars1 = ax1.bar(sheets, completion_rates, color=colors, alpha=0.7)
        ax1.set_title('Processing Completion by Sheet')
        ax1.set_ylabel('Completion Rate (%)')
        ax1.set_ylim(0, 100)
        ax1.tick_params(axis='x', rotation=45)

        # Add value labels
        for bar, rate in zip(bars1, completion_rates):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height + 1,
                    f'{rate:.1f}%', ha='center', va='bottom', fontsize=8)

        # Success rate comparison
        success_rates = [sheet_data[sheet].get('success_rate', 0) for sheet in sheets]

        bars2 = ax2.bar(sheets, success_rates, color=colors, alpha=0.7)
        ax2.set_title('Success Rate by Sheet')
        ax2.set_ylabel('Success Rate (%)')
        ax2.set_ylim(0, 100)
        ax2.tick_params(axis='x', rotation=45)

        for bar, rate in zip(bars2, success_rates):
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height + 1,
                    f'{rate:.1f}%', ha='center', va='bottom', fontsize=8)

        # Processing volume comparison
        volumes = [sheet_data[sheet].get('processed', 0) for sheet in sheets]

        bars3 = ax3.bar(sheets, volumes, color=colors, alpha=0.7)
        ax3.set_title('Processing Volume by Sheet')
        ax3.set_ylabel('Rows Processed')
        ax3.tick_params(axis='x', rotation=45)

        for bar, volume in zip(bars3, volumes):
            height = bar.get_height()
            ax3.text(bar.get_x() + bar.get_width()/2., height + height*0.01,
                    f'{volume:,}', ha='center', va='bottom', fontsize=8)

        # Average confidence comparison
        confidences = [sheet_data[sheet].get('avg_confidence', 0) for sheet in sheets]

        bars4 = ax4.bar(sheets, confidences, color=colors, alpha=0.7)
        ax4.set_title('Average Confidence by Sheet')
        ax4.set_ylabel('Average Confidence')
        ax4.set_ylim(0, 100)
        ax4.tick_params(axis='x', rotation=45)

        for bar, conf in zip(bars4, confidences):
            height = bar.get_height()
            ax4.text(bar.get_x() + bar.get_width()/2., height + 1,
                    f'{conf:.0f}', ha='center', va='bottom', fontsize=8)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=self.chart_config["dpi"], bbox_inches='tight')

        return fig

    def create_quality_analysis_chart(self, quality_data: Dict, save_path: str = None) -> plt.Figure:
        """Create data quality analysis charts."""
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10))

        overall_quality = quality_data.get("overall_quality", {})
        confidence_reliability = quality_data.get("confidence_reliability", {})
        completeness = quality_data.get("completeness_analysis", {})

        # Quality component scores
        components = overall_quality.get("component_scores", {})
        if components:
            comp_names = list(components.keys())
            comp_scores = list(components.values())

            bars1 = ax1.bar(comp_names, comp_scores, color='lightblue', alpha=0.7)
            ax1.set_title(f'Quality Components (Grade: {overall_quality.get("grade", "N/A")})')
            ax1.set_ylabel('Score')
            ax1.set_ylim(0, 100)
            ax1.tick_params(axis='x', rotation=45)

            # Add score labels
            for bar, score in zip(bars1, comp_scores):
                height = bar.get_height()
                ax1.text(bar.get_x() + bar.get_width()/2., height + 1,
                        f'{score:.1f}', ha='center', va='bottom', fontsize=8)

        # Confidence distribution
        dist_analysis = confidence_reliability.get("distribution_analysis", {})
        if dist_analysis and "buckets" in dist_analysis:
            buckets = dist_analysis["buckets"]
            labels = list(buckets.keys())
            values = list(buckets.values())

            bars2 = ax2.bar(labels, values, color='orange', alpha=0.7)
            ax2.set_title('Confidence Score Distribution')
            ax2.set_ylabel('Count')
            ax2.tick_params(axis='x', rotation=45)

        # Completeness by field
        by_field = completeness.get("by_field", {})
        if by_field:
            fields = list(by_field.keys())
            completion_rates = [by_field[field]["completion_rate"] for field in fields]

            bars3 = ax3.bar(fields, completion_rates, color='lightgreen', alpha=0.7)
            ax3.set_title('Data Completeness by Field')
            ax3.set_ylabel('Completion Rate (%)')
            ax3.set_ylim(0, 100)
            ax3.tick_params(axis='x', rotation=45)

            for bar, rate in zip(bars3, completion_rates):
                height = bar.get_height()
                ax3.text(bar.get_x() + bar.get_width()/2., height + 1,
                        f'{rate:.1f}%', ha='center', va='bottom', fontsize=8)

        # Quality grade visualization
        grade_scores = {
            "A": 95, "B": 85, "C": 75, "D": 65, "F": 50
        }
        current_grade = overall_quality.get("grade", "C")
        current_score = overall_quality.get("overall_score", 75)

        grades = list(grade_scores.keys())
        scores = list(grade_scores.values())
        colors = ['green' if g == current_grade else 'lightgray' for g in grades]

        bars4 = ax4.bar(grades, scores, color=colors, alpha=0.7)
        ax4.set_title(f'Quality Grade Scale (Current: {current_grade} - {current_score:.1f})')
        ax4.set_ylabel('Score Threshold')
        ax4.set_ylim(0, 100)

        # Add current score line
        ax4.axhline(y=current_score, color='red', linestyle='--', alpha=0.7, label=f'Current: {current_score:.1f}')
        ax4.legend()

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=self.chart_config["dpi"], bbox_inches='tight')

        return fig

    def create_performance_dashboard(self, performance_data: Dict, save_path: str = None) -> plt.Figure:
        """Create performance monitoring dashboard."""
        fig = plt.figure(figsize=(16, 10))

        # Create grid layout
        gs = fig.add_gridspec(3, 3, hspace=0.3, wspace=0.3)

        # Current system status
        ax1 = fig.add_subplot(gs[0, 0])
        system_perf = performance_data.get("system_performance", {})

        if system_perf:
            metrics = ['CPU', 'Memory', 'Chrome\nMemory']
            values = [
                system_perf.get('current_cpu', 0),
                system_perf.get('current_memory', 0),
                min(system_perf.get('chrome_memory_mb', 0) / 20, 100)  # Scale to 0-100
            ]
            colors = ['red' if v > 80 else 'orange' if v > 60 else 'green' for v in values]

            bars = ax1.bar(metrics, values, color=colors, alpha=0.7)
            ax1.set_title('System Resource Usage')
            ax1.set_ylabel('Usage (%)')
            ax1.set_ylim(0, 100)

            for bar, value in zip(bars, values):
                height = bar.get_height()
                ax1.text(bar.get_x() + bar.get_width()/2., height + 2,
                        f'{value:.0f}%', ha='center', va='bottom', fontsize=8)

        # Processing performance
        ax2 = fig.add_subplot(gs[0, 1])
        processing_perf = performance_data.get("processing_performance", {})

        if processing_perf:
            speeds = ['Current', 'Average', 'Peak']
            values = [
                processing_perf.get('current_speed', 0),
                processing_perf.get('avg_speed', 0),
                processing_perf.get('peak_speed', 0)
            ]

            bars = ax2.bar(speeds, values, color='skyblue', alpha=0.7)
            ax2.set_title('Processing Speed')
            ax2.set_ylabel('Rows/Second')

            for bar, value in zip(bars, values):
                height = bar.get_height()
                ax2.text(bar.get_x() + bar.get_width()/2., height + height*0.01,
                        f'{value:.1f}', ha='center', va='bottom', fontsize=8)

        # Network performance
        ax3 = fig.add_subplot(gs[0, 2])
        network_perf = performance_data.get("network_performance", {})

        if network_perf:
            ax3.text(0.5, 0.7, f'Avg Request Time:', ha='center', va='center',
                    transform=ax3.transAxes, fontsize=12, weight='bold')
            ax3.text(0.5, 0.5, f'{network_perf.get("avg_request_time", 0):.1f}s',
                    ha='center', va='center', transform=ax3.transAxes, fontsize=20)
            ax3.text(0.5, 0.3, f'Slow Requests: {network_perf.get("slow_requests", 0)}',
                    ha='center', va='center', transform=ax3.transAxes, fontsize=10)

        ax3.set_title('Network Performance')
        ax3.axis('off')

        # Session history (spans 2 columns)
        ax4 = fig.add_subplot(gs[1, :2])
        session_history = performance_data.get("session_history", {})
        recent_sessions = session_history.get("recent_sessions", [])

        if recent_sessions:
            sheets = [s["sheet"] for s in recent_sessions]
            durations = [s["duration"] for s in recent_sessions]
            success_rates = [s["success_rate"] for s in recent_sessions]

            x = range(len(sheets))
            width = 0.35

            bars1 = ax4.bar([i - width/2 for i in x], durations, width,
                           label='Duration (min)', color='lightblue', alpha=0.7)

            ax5 = ax4.twinx()
            bars2 = ax5.bar([i + width/2 for i in x], success_rates, width,
                           label='Success Rate (%)', color='lightgreen', alpha=0.7)

            ax4.set_xlabel('Recent Sessions')
            ax4.set_ylabel('Duration (minutes)')
            ax5.set_ylabel('Success Rate (%)')
            ax4.set_title('Recent Session Performance')
            ax4.set_xticks(x)
            ax4.set_xticklabels([f'{s[:8]}...' for s in sheets], rotation=45)

            ax4.legend(loc='upper left')
            ax5.legend(loc='upper right')
        else:
            ax4.text(0.5, 0.5, 'No recent session data', ha='center', va='center',
                    transform=ax4.transAxes, fontsize=14)
            ax4.set_title('Recent Session Performance')

        # Performance recommendations
        ax6 = fig.add_subplot(gs[1:, 2])
        recommendations = performance_data.get("optimization_recommendations", [])

        rec_text = "OPTIMIZATION RECOMMENDATIONS:\n\n"
        for i, rec in enumerate(recommendations[:8], 1):
            rec_text += f"{i}. {rec[:50]}...\n\n" if len(rec) > 50 else f"{i}. {rec}\n\n"

        if not recommendations:
            rec_text = "No specific optimization\nrecommendations at this time.\n\nSystem performance is good."

        ax6.text(0.05, 0.95, rec_text, transform=ax6.transAxes, fontsize=8,
                verticalalignment='top', wrap=True)
        ax6.set_title('Performance Recommendations')
        ax6.axis('off')

        # Error analysis
        ax7 = fig.add_subplot(gs[2, :2])
        error_analysis = performance_data.get("error_analysis", {})

        if error_analysis and error_analysis.get("total_errors", 0) > 0:
            error_types = error_analysis.get("error_types", {})
            if error_types:
                types = list(error_types.keys())
                counts = list(error_types.values())

                bars = ax7.bar(types, counts, color='red', alpha=0.6)
                ax7.set_title(f'Error Analysis (Total: {error_analysis.get("total_errors", 0)})')
                ax7.set_ylabel('Error Count')
                ax7.tick_params(axis='x', rotation=45)

                for bar, count in zip(bars, counts):
                    height = bar.get_height()
                    ax7.text(bar.get_x() + bar.get_width()/2., height + height*0.01,
                            f'{count}', ha='center', va='bottom', fontsize=8)
        else:
            ax7.text(0.5, 0.5, 'No significant errors detected', ha='center', va='center',
                    transform=ax7.transAxes, fontsize=14, color='green')
            ax7.set_title('Error Analysis')

        if save_path:
            plt.savefig(save_path, dpi=self.chart_config["dpi"], bbox_inches='tight')

        return fig

    def create_trend_analysis_chart(self, trend_data: Dict, save_path: str = None) -> plt.Figure:
        """Create trend analysis visualization."""
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10))

        processing_trends = trend_data.get("processing_trends", {})
        success_trends = trend_data.get("success_rate_trends", {})
        enhancement_impact = trend_data.get("enhancement_impact", {})

        # Processing volume trend
        daily_volumes = processing_trends.get("daily_volumes", {})
        if daily_volumes:
            dates = list(daily_volumes.keys())
            volumes = list(daily_volumes.values())

            ax1.plot(dates, volumes, marker='o', color='blue', alpha=0.7)
            ax1.set_title('Processing Volume Trend')
            ax1.set_ylabel('Daily Volume')
            ax1.tick_params(axis='x', rotation=45)

            # Add trend line
            if len(volumes) > 2:
                z = pd.Series(volumes).rolling(window=3).mean()
                ax1.plot(dates, z, color='red', alpha=0.5, linestyle='--', label='Trend')
                ax1.legend()

        # Processing speed trend
        daily_speeds = processing_trends.get("daily_speeds", {})
        if daily_speeds:
            dates = list(daily_speeds.keys())
            speeds = list(daily_speeds.values())

            ax2.plot(dates, speeds, marker='s', color='green', alpha=0.7)
            ax2.set_title('Processing Speed Trend')
            ax2.set_ylabel('Rows/Hour')
            ax2.tick_params(axis='x', rotation=45)

        # Success rate by sheet trend
        by_sheet = success_trends.get("by_sheet", {})
        if by_sheet:
            for i, (sheet, data_points) in enumerate(list(by_sheet.items())[:3]):  # Show top 3 sheets
                if data_points:
                    dates = [dp["date"] for dp in data_points]
                    rates = [dp["rate"] for dp in data_points]

                    color = self.color_schemes["sheets"][i % len(self.color_schemes["sheets"])]
                    ax3.plot(dates, rates, marker='o', label=sheet, color=color, alpha=0.7)

            ax3.set_title('Success Rate Trends by Sheet')
            ax3.set_ylabel('Success Rate (%)')
            ax3.set_ylim(0, 100)
            ax3.tick_params(axis='x', rotation=45)
            ax3.legend()

        # Enhancement impact
        enhancement_data = enhancement_impact.get("enhancement_data", {})
        if enhancement_data:
            types = list(enhancement_data.keys())
            success_rates = [enhancement_data[t]["avg_success_rate"] for t in types]

            bars = ax4.bar(types, success_rates,
                          color=['lightblue' if t == 'standard' else 'lightgreen' for t in types],
                          alpha=0.7)
            ax4.set_title('Enhancement Impact Comparison')
            ax4.set_ylabel('Success Rate (%)')
            ax4.set_ylim(0, 100)

            for bar, rate in zip(bars, success_rates):
                height = bar.get_height()
                ax4.text(bar.get_x() + bar.get_width()/2., height + 1,
                        f'{rate:.1f}%', ha='center', va='bottom', fontsize=8)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=self.chart_config["dpi"], bbox_inches='tight')

        return fig

    def create_comprehensive_report_chart(self, all_data: Dict, save_path: str = None) -> plt.Figure:
        """Create comprehensive overview chart combining all analytics."""
        fig = plt.figure(figsize=(20, 12))
        gs = fig.add_gridspec(4, 4, hspace=0.4, wspace=0.4)

        overview = all_data.get("overview", {})
        quality = all_data.get("quality", {})
        performance = all_data.get("performance", {})
        trends = all_data.get("trends", {})

        # Key metrics summary (top row)
        ax1 = fig.add_subplot(gs[0, :2])

        metrics_text = f"""
PARTS AGENT ANALYTICS DASHBOARD
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

PROCESSING OVERVIEW:
• Total Rows: {overview.get('total_rows', 0):,}
• Processed: {overview.get('processed_rows', 0):,} ({overview.get('processing_completion', 0):.1f}%)
• Success Rate: {overview.get('success_rate', 0):.1f}%
• Ready for Enhancement: {overview.get('needs_review', 0):,} UNCERTAIN rows

QUALITY ASSESSMENT:
• Overall Score: {quality.get('overall_quality', {}).get('overall_score', 0):.1f}
• Grade: {quality.get('overall_quality', {}).get('grade', 'N/A')}
• Data Quality: {['Poor', 'Fair', 'Good', 'Excellent'][min(3, int(quality.get('overall_quality', {}).get('overall_score', 0) // 25))]}
        """

        ax1.text(0.05, 0.95, metrics_text.strip(), transform=ax1.transAxes, fontsize=11,
                verticalalignment='top', family='monospace')
        ax1.set_title('Executive Summary', fontsize=14, weight='bold')
        ax1.axis('off')

        # Processing status pie chart
        ax2 = fig.add_subplot(gs[0, 2])
        if overview.get('processed_rows', 0) > 0:
            labels = ['YES', 'LIKELY', 'UNCERTAIN', 'NO']
            sizes = [overview.get(label, 0) for label in labels]
            colors = [self.color_schemes["match_results"][label] for label in labels]

            wedges, texts, autotexts = ax2.pie(sizes, labels=labels, colors=colors,
                                             autopct='%1.1f%%', startangle=90)
            ax2.set_title('Match Results')

        # Quality gauge
        ax3 = fig.add_subplot(gs[0, 3])
        quality_score = quality.get('overall_quality', {}).get('overall_score', 0)

        # Create gauge chart
        theta = (quality_score / 100) * 180  # Convert to degrees
        ax3.pie([quality_score, 100-quality_score], colors=['green' if quality_score > 80 else 'orange' if quality_score > 60 else 'red', 'lightgray'],
               startangle=180, counterclock=False)
        ax3.text(0, -0.5, f'{quality_score:.1f}', ha='center', va='center', fontsize=16, weight='bold')
        ax3.set_title('Quality Score')

        # Add more comprehensive charts in remaining space
        # This would continue with additional visualizations...

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=self.chart_config["dpi"], bbox_inches='tight')

        return fig

    def export_all_charts(self, export_dir: str, data: Dict):
        """Export all chart types for comprehensive reporting."""
        export_path = Path(export_dir)
        export_path.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Export individual chart types
        chart_exports = [
            ("processing_status", self.create_processing_status_chart),
            ("sheet_comparison", self.create_sheet_comparison_chart),
            ("quality_analysis", self.create_quality_analysis_chart),
            ("performance_dashboard", self.create_performance_dashboard),
            ("trend_analysis", self.create_trend_analysis_chart),
            ("comprehensive_report", self.create_comprehensive_report_chart)
        ]

        exported_files = []

        for chart_name, chart_func in chart_exports:
            try:
                filename = f"{chart_name}_{timestamp}.png"
                filepath = export_path / filename

                # Create appropriate data subset for each chart
                if chart_name in ["processing_status", "sheet_comparison"]:
                    chart_data = data.get("overview", {})
                elif chart_name == "quality_analysis":
                    chart_data = data.get("quality", {})
                elif chart_name == "performance_dashboard":
                    chart_data = data.get("performance", {})
                elif chart_name == "trend_analysis":
                    chart_data = data.get("trends", {})
                else:
                    chart_data = data

                fig = chart_func(chart_data, str(filepath))
                plt.close(fig)  # Close to free memory

                exported_files.append(filename)

            except Exception as e:
                print(f"Error exporting {chart_name}: {e}")

        return exported_files