"""
Launch Web Dashboard
Enhanced User Experience & Web Interface (Priority 2)

Standalone launcher for the Flask web dashboard.
Run this script to start the web interface at http://localhost:5000
"""

import sys
from pathlib import Path

# Add parent directory for imports
sys.path.insert(0, str(Path(__file__).parent))

def launch_dashboard():
    """Launch the web dashboard."""
    print("Parts Agent - Web Dashboard Launcher")
    print("=" * 50)
    print("Starting Flask web application...")
    print("")

    try:
        # Import and run the Flask app
        from web.app import app, socketio, initialize_analytics

        print("1. Initializing analytics components...")
        if initialize_analytics():
            print("   [OK] Analytics components initialized successfully")
        else:
            print("   [WARNING] Analytics components failed to initialize")
            print("   - Web interface will work with limited functionality")

        print("")
        print("2. Starting Flask server...")
        print("   - Host: 0.0.0.0 (accessible from other devices)")
        print("   - Port: 5000")
        print("   - Debug mode: Enabled")
        print("")
        print("Web Dashboard URLs:")
        print("   - Local access: http://localhost:5000")
        print("   - Network access: http://0.0.0.0:5000")
        print("")
        print("Available Sections:")
        print("   - Overview: System status and match distribution")
        print("   - Processing: Start/stop processing with real-time progress")
        print("   - Analytics: Advanced statistics and trend analysis")
        print("   - Performance: System resource monitoring")
        print("   - Quality: Data quality analysis and scoring")
        print("   - Export: Download analytics data as JSON")
        print("")
        print("Real-time Features:")
        print("   - WebSocket connection for live updates")
        print("   - Auto-refresh every 30 seconds")
        print("   - Live processing progress tracking")
        print("   - System performance monitoring")
        print("")
        print("Press Ctrl+C to stop the server")
        print("=" * 50)

        # Run the Flask application with SocketIO
        socketio.run(app, host='0.0.0.0', port=5000, debug=True)

    except KeyboardInterrupt:
        print("\n\nShutting down web dashboard...")
        print("Thank you for using Parts Agent Web Interface!")

    except Exception as e:
        print(f"\nERROR: Failed to start web dashboard: {e}")
        print("\nTroubleshooting:")
        print("1. Ensure all dependencies are installed:")
        print("   uv add flask flask-socketio requests")
        print("2. Check that port 5000 is available")
        print("3. Verify analytics components are working:")
        print("   uv run python src/test_analytics_system.py")
        print("")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    launch_dashboard()