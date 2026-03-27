"""
Test Script for Analytics Dashboard

Tests the analytics dashboard with actual data to ensure proper functionality.
"""

import tkinter as tk
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from analytics.dashboard import AnalyticsDashboard

class TestDashboardApp:
    """Simple test application for the analytics dashboard."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Analytics Dashboard Test")
        self.root.geometry("600x400")

        # Create main frame
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

        # Title
        title_label = tk.Label(main_frame, text="Parts Agent Analytics Dashboard Test",
                              font=("Arial", 16, "bold"))
        title_label.pack(pady=10)

        # Info label
        info_label = tk.Label(main_frame,
                             text="Click the button below to open the analytics dashboard.\n"
                                  "The dashboard will load data from the Excel file and display\n"
                                  "comprehensive analytics and visualizations.",
                             font=("Arial", 10),
                             justify=tk.CENTER)
        info_label.pack(pady=20)

        # Dashboard button
        dashboard_button = tk.Button(main_frame, text="Open Analytics Dashboard",
                                    command=self.open_dashboard,
                                    font=("Arial", 12),
                                    bg="lightblue",
                                    padx=20, pady=10)
        dashboard_button.pack(pady=20)

        # Status label
        self.status_label = tk.Label(main_frame, text="Ready", fg="green")
        self.status_label.pack(pady=10)

        # Initialize dashboard
        self.dashboard = None

    def open_dashboard(self):
        """Open the analytics dashboard."""
        try:
            self.status_label.config(text="Initializing dashboard...", fg="blue")
            self.root.update()

            # Create dashboard instance if not exists
            if not self.dashboard:
                self.dashboard = AnalyticsDashboard(self.root)

            # Show dashboard
            self.dashboard.show_dashboard()

            self.status_label.config(text="Dashboard opened successfully!", fg="green")

        except Exception as e:
            self.status_label.config(text=f"Error: {str(e)}", fg="red")
            print(f"Dashboard error: {e}")
            import traceback
            traceback.print_exc()

    def run(self):
        """Run the test application."""
        self.root.mainloop()

def main():
    """Main entry point for dashboard testing."""
    print("Starting Analytics Dashboard Test...")
    print("This will test the complete dashboard functionality.")
    print()

    try:
        app = TestDashboardApp()
        app.run()
    except Exception as e:
        print(f"Failed to start dashboard test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()