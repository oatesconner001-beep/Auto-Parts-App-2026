"""
Parts Agent Web Application
Enhanced User Experience & Web Interface (Priority 2)

Modern web dashboard with Flask providing:
- Real-time processing progress with WebSocket updates
- Interactive result browsing with filtering and sorting
- Mobile-responsive design for remote monitoring
- REST API endpoints for system integration
"""

from flask import Flask, render_template, jsonify, request, send_file
from flask_socketio import SocketIO, emit
import os
import sys
import json
import time
import threading
from pathlib import Path
from datetime import datetime
import logging

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from analytics.stats_engine import StatsEngine
from analytics.trend_analyzer import TrendAnalyzer
from analytics.performance_metrics import PerformanceTracker
from analytics.data_quality import DataQualityAnalyzer

app = Flask(__name__)
app.config['SECRET_KEY'] = 'parts-agent-web-2026'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global analytics components
analytics_components = {
    'stats_engine': None,
    'trend_analyzer': None,
    'performance_tracker': None,
    'quality_analyzer': None
}

# Global status tracking
system_status = {
    'processing_active': False,
    'current_sheet': None,
    'progress': {'current': 0, 'total': 0, 'percentage': 0},
    'last_update': datetime.now().isoformat(),
    'session_start': datetime.now().isoformat()
}

def initialize_analytics():
    """Initialize analytics components for web interface."""
    try:
        excel_path = Path(__file__).parent.parent.parent / "FISHER SKP INTERCHANGE 20260302.xlsx"

        analytics_components['stats_engine'] = StatsEngine(str(excel_path))
        analytics_components['trend_analyzer'] = TrendAnalyzer(str(excel_path))
        analytics_components['performance_tracker'] = PerformanceTracker()
        analytics_components['quality_analyzer'] = DataQualityAnalyzer(str(excel_path))

        app.logger.info("Analytics components initialized successfully")
        return True

    except Exception as e:
        app.logger.error(f"Failed to initialize analytics: {e}")
        return False

@app.route('/')
def dashboard():
    """Main dashboard page."""
    return render_template('dashboard.html')

@app.route('/api/status')
def api_status():
    """Get current system status."""
    try:
        # Update performance metrics if available
        if analytics_components['performance_tracker']:
            perf_data = analytics_components['performance_tracker'].get_system_metrics()
            system_status['performance'] = perf_data

        system_status['last_update'] = datetime.now().isoformat()
        return jsonify(system_status)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/analytics/overview')
def api_analytics_overview():
    """Get analytics overview data."""
    try:
        if not analytics_components['stats_engine']:
            return jsonify({'error': 'Analytics not initialized'}), 500

        stats = analytics_components['stats_engine'].get_comprehensive_statistics()

        overview = {
            'total_rows': stats.get('processing_summary', {}).get('total_rows', 0),
            'processed_rows': stats.get('processing_summary', {}).get('processed_rows', 0),
            'processing_rate': stats.get('processing_summary', {}).get('processing_percentage', 0),
            'match_distribution': stats.get('match_distribution', {}),
            'brand_statistics': stats.get('brand_statistics', {}),
            'timestamp': datetime.now().isoformat()
        }

        return jsonify(overview)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/analytics/performance')
def api_analytics_performance():
    """Get performance analytics data."""
    try:
        if not analytics_components['performance_tracker']:
            return jsonify({'error': 'Performance tracker not initialized'}), 500

        performance_data = analytics_components['performance_tracker'].get_system_metrics()
        return jsonify(performance_data)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/analytics/quality')
def api_analytics_quality():
    """Get data quality analytics."""
    try:
        if not analytics_components['quality_analyzer']:
            return jsonify({'error': 'Quality analyzer not initialized'}), 500

        quality_analysis = analytics_components['quality_analyzer'].analyze_data_quality()
        return jsonify(quality_analysis)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/analytics/trends')
def api_analytics_trends():
    """Get trend analysis data."""
    try:
        if not analytics_components['trend_analyzer']:
            return jsonify({'error': 'Trend analyzer not initialized'}), 500

        trend_analysis = analytics_components['trend_analyzer'].analyze_trends()
        return jsonify(trend_analysis)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/processing/start', methods=['POST'])
def api_start_processing():
    """Start processing for a specific sheet."""
    try:
        data = request.get_json() or {}
        sheet_name = data.get('sheet_name')
        limit = data.get('limit', 50)

        if not sheet_name:
            return jsonify({'error': 'Sheet name required'}), 400

        # Update system status
        system_status['processing_active'] = True
        system_status['current_sheet'] = sheet_name
        system_status['progress'] = {'current': 0, 'total': limit, 'percentage': 0}

        # Emit status update via WebSocket
        socketio.emit('status_update', system_status)

        # Note: Actual processing would be started here via subprocess
        # For now, we simulate the status update

        return jsonify({
            'status': 'started',
            'sheet_name': sheet_name,
            'limit': limit,
            'message': f'Processing started for {sheet_name} with limit {limit}'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/processing/stop', methods=['POST'])
def api_stop_processing():
    """Stop current processing."""
    try:
        system_status['processing_active'] = False
        system_status['current_sheet'] = None

        socketio.emit('status_update', system_status)

        return jsonify({
            'status': 'stopped',
            'message': 'Processing stopped'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/export/<data_type>')
def api_export_data(data_type):
    """Export analytics data as JSON."""
    try:
        if data_type == 'overview' and analytics_components['stats_engine']:
            data = analytics_components['stats_engine'].get_comprehensive_statistics()
        elif data_type == 'performance' and analytics_components['performance_tracker']:
            data = analytics_components['performance_tracker'].get_system_metrics()
        elif data_type == 'quality' and analytics_components['quality_analyzer']:
            data = analytics_components['quality_analyzer'].analyze_data_quality()
        elif data_type == 'trends' and analytics_components['trend_analyzer']:
            data = analytics_components['trend_analyzer'].analyze_trends()
        else:
            return jsonify({'error': f'Unknown data type: {data_type}'}), 400

        # Create temporary export file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"parts_agent_{data_type}_{timestamp}.json"
        export_path = Path(__file__).parent.parent.parent / "output" / filename

        # Ensure output directory exists
        export_path.parent.mkdir(exist_ok=True)

        with open(export_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)

        return send_file(export_path, as_attachment=True, download_name=filename)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# WebSocket events
@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    emit('status_update', system_status)
    app.logger.info(f"Client connected")

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    app.logger.info("Client disconnected")

@socketio.on('request_update')
def handle_request_update():
    """Handle client request for status update."""
    emit('status_update', system_status)

def background_monitor():
    """Background thread to monitor system status and emit updates."""
    while True:
        try:
            if analytics_components['performance_tracker']:
                perf_data = analytics_components['performance_tracker'].get_system_metrics()
                system_status['performance'] = perf_data
                system_status['last_update'] = datetime.now().isoformat()

                # Emit to all connected clients
                socketio.emit('performance_update', perf_data)

        except Exception as e:
            app.logger.error(f"Background monitor error: {e}")

        time.sleep(5)  # Update every 5 seconds

if __name__ == '__main__':
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Initialize analytics
    if initialize_analytics():
        app.logger.info("Web application starting with analytics support")
    else:
        app.logger.warning("Web application starting without analytics")

    # Start background monitoring thread
    monitor_thread = threading.Thread(target=background_monitor, daemon=True)
    monitor_thread.start()

    # Run the web application
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)