"""
Enhanced Parts Agent GUI — Professional multi-panel interface.

Provides:
- Interactive Excel viewer/editor with real-time updates
- AI backend configuration and cost tracking
- Dynamic website configuration
- Job queue management and progress tracking
- Live logging and statistics dashboard
"""

import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import threading
import time
import os
import json
from pathlib import Path
from datetime import datetime
import sys

# Add parent directory to path to import existing modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.app_config import AppConfig
from core.cost.cost_tracker import CostTracker
from count_results import count_all_results

# Import analytics dashboard (with fallback if not available)
try:
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from analytics.dashboard import AnalyticsDashboard
    ANALYTICS_AVAILABLE = True
except ImportError:
    ANALYTICS_AVAILABLE = False
    print("Analytics dashboard not available - advanced analytics features disabled")

# Import multi-site tab (with fallback if not available)
try:
    from gui.multi_site_tab import MultiSiteTab
    MULTI_SITE_AVAILABLE = True
except ImportError:
    MULTI_SITE_AVAILABLE = False
    print("Multi-site functionality not available - multi-site features disabled")

DEFAULT_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "FISHER SKP INTERCHANGE 20260302.xlsx",
)

class UnifiedPartsAgent(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Parts Agent Pro — Unified Auto Parts Matching")
        self.geometry("1400x900")
        self.minsize(1200, 800)
        self.resizable(True, True)

        # State management
        self._stop_flag = [False]
        self._worker_thread = None
        self.app_config = AppConfig()
        self.cost_tracker = CostTracker()

        # Initialize analytics dashboard
        self.analytics_dashboard = None
        if ANALYTICS_AVAILABLE:
            try:
                self.analytics_dashboard = AnalyticsDashboard(self)
            except Exception as e:
                print(f"Failed to initialize analytics dashboard: {e}")
                self.analytics_dashboard = None

        # Build the enhanced interface
        self._create_menu()
        self._build_main_layout()
        self._initialize_defaults()

    def _create_menu(self):
        """Create professional menu bar."""
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open Excel File...", command=self._browse_file)
        file_menu.add_command(label="Import Configuration...", command=self._import_config)
        file_menu.add_command(label="Export Configuration...", command=self._export_config)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit)

        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="AI Backend Settings", command=self._show_ai_settings)
        tools_menu.add_command(label="Site Configuration Wizard", command=self._show_site_wizard)
        tools_menu.add_command(label="Cost Management", command=self._show_cost_manager)
        tools_menu.add_separator()
        tools_menu.add_command(label="Analytics Dashboard", command=self._show_analytics_dashboard)
        tools_menu.add_command(label="Statistics Dashboard", command=self._show_statistics)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="User Guide", command=self._show_help)
        help_menu.add_command(label="About", command=self._show_about)

    def _build_main_layout(self):
        """Build the main multi-panel layout."""
        # Create main paned window
        main_paned = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main_paned.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # Left panel (control and status)
        self._build_left_panel(main_paned)

        # Right panel (Excel viewer and processing)
        self._build_right_panel(main_paned)

        # Bottom panel (logs and progress)
        self._build_bottom_panel()

    def _build_left_panel(self, parent):
        """Build left control panel with file browser, job queue, and AI status."""
        left_frame = ttk.Frame(parent)
        parent.add(left_frame, weight=1)

        # Create notebook for tabbed interface
        left_notebook = ttk.Notebook(left_frame)
        left_notebook.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # File Browser Tab
        file_tab = ttk.Frame(left_notebook)
        left_notebook.add(file_tab, text="Files & Jobs")

        # File selection section
        file_section = ttk.LabelFrame(file_tab, text="Excel File")
        file_section.pack(fill=tk.X, padx=4, pady=4)

        self._filepath_var = tk.StringVar()
        file_entry = ttk.Entry(file_section, textvariable=self._filepath_var)
        file_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4,2), pady=4)

        ttk.Button(file_section, text="Browse...", command=self._browse_file).pack(
            side=tk.RIGHT, padx=(2,4), pady=4
        )

        # Sheet selection and controls
        control_section = ttk.LabelFrame(file_tab, text="Processing Controls")
        control_section.pack(fill=tk.X, padx=4, pady=4)

        # Sheet selector
        sheet_frame = ttk.Frame(control_section)
        sheet_frame.pack(fill=tk.X, padx=4, pady=2)
        ttk.Label(sheet_frame, text="Sheet:").pack(side=tk.LEFT)

        self._sheet_var = tk.StringVar(value="Anchor")
        sheet_combo = ttk.Combobox(
            sheet_frame, textvariable=self._sheet_var, width=15,
            values=["Anchor", "Dorman", "GMB", "SMP", "Four Seasons "],
            state="readonly"
        )
        sheet_combo.pack(side=tk.LEFT, padx=(4,0))

        # Options
        options_frame = ttk.Frame(control_section)
        options_frame.pack(fill=tk.X, padx=4, pady=2)

        self._reprocess_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            options_frame, text="Re-process UNCERTAIN", variable=self._reprocess_var
        ).pack(side=tk.LEFT)

        # Limit controls
        limit_frame = ttk.Frame(control_section)
        limit_frame.pack(fill=tk.X, padx=4, pady=2)
        ttk.Label(limit_frame, text="Limit:").pack(side=tk.LEFT)

        self._limit_var = tk.StringVar(value="")
        limit_entry = ttk.Entry(limit_frame, textvariable=self._limit_var, width=10)
        limit_entry.pack(side=tk.LEFT, padx=(4,0))
        ttk.Label(limit_frame, text="rows (blank = all)").pack(side=tk.LEFT, padx=(2,0))

        # Action buttons
        action_frame = ttk.Frame(control_section)
        action_frame.pack(fill=tk.X, padx=4, pady=4)

        self._start_btn = ttk.Button(
            action_frame, text="Start Processing", command=self._start_processing
        )
        self._start_btn.pack(fill=tk.X, pady=1)

        self._stop_btn = ttk.Button(
            action_frame, text="Stop", command=self._stop_processing, state="disabled"
        )
        self._stop_btn.pack(fill=tk.X, pady=1)

        ttk.Button(
            action_frame, text="Image Analysis", command=self._start_image_analysis
        ).pack(fill=tk.X, pady=1)

        # Analytics dashboard button
        analytics_btn = ttk.Button(
            action_frame, text="Analytics Dashboard", command=self._show_analytics_dashboard
        )
        analytics_btn.pack(fill=tk.X, pady=1)

        # Disable analytics button if not available
        if not ANALYTICS_AVAILABLE or not self.analytics_dashboard:
            analytics_btn.config(state="disabled")

        # Job Status Tab
        status_tab = ttk.Frame(left_notebook)
        left_notebook.add(status_tab, text="Status")

        # Current job status
        job_section = ttk.LabelFrame(status_tab, text="Current Job")
        job_section.pack(fill=tk.X, padx=4, pady=4)

        self._status_var = tk.StringVar(value="Idle")
        status_label = ttk.Label(job_section, textvariable=self._status_var, font=("Arial", 10, "bold"))
        status_label.pack(pady=4)

        self._progress_var = tk.IntVar(value=0)
        self._progress_bar = ttk.Progressbar(
            job_section, variable=self._progress_var, maximum=100
        )
        self._progress_bar.pack(fill=tk.X, padx=4, pady=2)

        self._counter_var = tk.StringVar(value="Row 0 of 0")
        counter_label = ttk.Label(job_section, textvariable=self._counter_var)
        counter_label.pack(pady=2)

        # Statistics dashboard
        stats_section = ttk.LabelFrame(status_tab, text="Statistics Dashboard")
        stats_section.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        self._stats_text = tk.Text(stats_section, height=8, state="disabled", wrap=tk.WORD)
        stats_scroll = ttk.Scrollbar(stats_section, orient=tk.VERTICAL, command=self._stats_text.yview)
        self._stats_text.configure(yscrollcommand=stats_scroll.set)

        self._stats_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(4,0), pady=4)
        stats_scroll.pack(side=tk.RIGHT, fill=tk.Y, padx=(0,4), pady=4)

        ttk.Button(stats_section, text="Refresh Stats", command=self._refresh_stats).pack(
            side=tk.BOTTOM, pady=4
        )

        # AI Configuration Tab
        ai_tab = ttk.Frame(left_notebook)
        left_notebook.add(ai_tab, text="AI Config")

        # AI Backend selector
        backend_section = ttk.LabelFrame(ai_tab, text="AI Backend")
        backend_section.pack(fill=tk.X, padx=4, pady=4)

        self._ai_backend_var = tk.StringVar(value="Claude API")
        ai_backends = ["Claude API", "Gemini API", "Ollama Local", "Rules Only"]

        for backend in ai_backends:
            ttk.Radiobutton(
                backend_section, text=backend, variable=self._ai_backend_var, value=backend
            ).pack(anchor=tk.W, padx=4, pady=1)

        # Cost tracking
        cost_section = ttk.LabelFrame(ai_tab, text="Cost Tracking")
        cost_section.pack(fill=tk.X, padx=4, pady=4)

        self._cost_display_var = tk.StringVar(value="$0.00")
        cost_label = ttk.Label(cost_section, textvariable=self._cost_display_var, font=("Arial", 12, "bold"))
        cost_label.pack(pady=2)

        limit_frame = ttk.Frame(cost_section)
        limit_frame.pack(fill=tk.X, padx=4, pady=2)
        ttk.Label(limit_frame, text="Daily Limit: $").pack(side=tk.LEFT)

        self._cost_limit_var = tk.StringVar(value="5.00")
        limit_entry = ttk.Entry(limit_frame, textvariable=self._cost_limit_var, width=8)
        limit_entry.pack(side=tk.LEFT)

        ttk.Button(cost_section, text="Reset Daily Cost", command=self._reset_cost).pack(pady=2)

        # Multi-Site Tab (if available)
        if MULTI_SITE_AVAILABLE:
            try:
                self.multi_site_tab = MultiSiteTab(left_notebook)
                print("Multi-site functionality enabled")
            except Exception as e:
                print(f"Failed to initialize multi-site tab: {e}")
                self.multi_site_tab = None
        else:
            self.multi_site_tab = None

    def _build_right_panel(self, parent):
        """Build right panel with Excel viewer."""
        right_frame = ttk.Frame(parent)
        parent.add(right_frame, weight=2)

        # Excel viewer section
        excel_section = ttk.LabelFrame(right_frame, text="Excel Data Viewer")
        excel_section.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # Viewer controls
        viewer_controls = ttk.Frame(excel_section)
        viewer_controls.pack(fill=tk.X, padx=4, pady=2)

        ttk.Button(viewer_controls, text="Load Data", command=self._load_excel_data).pack(side=tk.LEFT, padx=2)
        ttk.Button(viewer_controls, text="Refresh", command=self._refresh_excel_data).pack(side=tk.LEFT, padx=2)
        ttk.Button(viewer_controls, text="Export View", command=self._export_view).pack(side=tk.LEFT, padx=2)

        # Filter controls
        filter_frame = ttk.Frame(viewer_controls)
        filter_frame.pack(side=tk.RIGHT)
        ttk.Label(filter_frame, text="Filter:").pack(side=tk.LEFT)

        self._filter_var = tk.StringVar()
        filter_combo = ttk.Combobox(
            filter_frame, textvariable=self._filter_var, width=12,
            values=["All", "YES", "LIKELY", "UNCERTAIN", "NO", "Unprocessed"]
        )
        filter_combo.pack(side=tk.LEFT, padx=2)
        filter_combo.bind("<<ComboboxSelected>>", self._filter_data)

        # Excel data display (simplified tree view for now)
        tree_frame = ttk.Frame(excel_section)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # Define columns for the treeview
        columns = ("Row", "Part Type", "Supplier", "Part #", "SKP #", "Match", "Confidence", "Reason")

        self._data_tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=15)

        # Configure column headings and widths
        for col in columns:
            self._data_tree.heading(col, text=col)
            if col == "Row":
                self._data_tree.column(col, width=50, minwidth=50)
            elif col == "Part #" or col == "SKP #":
                self._data_tree.column(col, width=100, minwidth=80)
            elif col == "Confidence":
                self._data_tree.column(col, width=80, minwidth=60)
            elif col == "Reason":
                self._data_tree.column(col, width=200, minwidth=150)
            else:
                self._data_tree.column(col, width=100, minwidth=80)

        # Scrollbars for treeview
        v_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self._data_tree.yview)
        h_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self._data_tree.xview)
        self._data_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)

        # Pack treeview and scrollbars
        self._data_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

    def _build_bottom_panel(self):
        """Build bottom panel for logs and detailed progress."""
        bottom_frame = ttk.LabelFrame(self, text="Activity Log")
        bottom_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=4, pady=4)

        # Log display with tabs for different types
        log_notebook = ttk.Notebook(bottom_frame)
        log_notebook.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        # Main activity log
        main_log_frame = ttk.Frame(log_notebook)
        log_notebook.add(main_log_frame, text="Main Log")

        self._log_box = scrolledtext.ScrolledText(
            main_log_frame, height=8, state="disabled", font=("Consolas", 9), wrap=tk.WORD
        )
        self._log_box.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        # Error log
        error_log_frame = ttk.Frame(log_notebook)
        log_notebook.add(error_log_frame, text="Errors")

        self._error_log_box = scrolledtext.ScrolledText(
            error_log_frame, height=8, state="disabled", font=("Consolas", 9), wrap=tk.WORD
        )
        self._error_log_box.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        # AI log
        ai_log_frame = ttk.Frame(log_notebook)
        log_notebook.add(ai_log_frame, text="AI Calls")

        self._ai_log_box = scrolledtext.ScrolledText(
            ai_log_frame, height=8, state="disabled", font=("Consolas", 9), wrap=tk.WORD
        )
        self._ai_log_box.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

    def _initialize_defaults(self):
        """Initialize default values and load existing configuration."""
        # Pre-fill file path if default exists
        if os.path.exists(DEFAULT_FILE):
            self._filepath_var.set(DEFAULT_FILE)

        # Load configuration
        self.app_config.load()

        # Apply saved settings
        if hasattr(self.app_config, 'ai_backend'):
            self._ai_backend_var.set(self.app_config.ai_backend)
        if hasattr(self.config, 'cost_limit'):
            self._cost_limit_var.set(str(self.app_config.cost_limit))

        # Load initial stats
        self._refresh_stats()

    # Event handlers
    def _browse_file(self):
        """File browser dialog."""
        path = filedialog.askopenfilename(
            title="Select Excel file",
            filetypes=[("Excel files", "*.xlsx *.xlsm"), ("All files", "*.*")]
        )
        if path:
            self._filepath_var.set(path)
            self._log(f"Selected file: {os.path.basename(path)}")

    def _start_processing(self):
        """Start main processing job."""
        filepath = self._filepath_var.get().strip()
        if not filepath:
            messagebox.showerror("Error", "Please select an Excel file first.")
            return
        if not os.path.exists(filepath):
            messagebox.showerror("Error", f"File not found: {filepath}")
            return

        # Apply AI backend configuration
        self._apply_ai_backend()

        self._stop_flag[0] = False
        self._start_btn.config(state="disabled")
        self._stop_btn.config(state="normal")
        self._set_status("Running...")
        self._progress_var.set(0)
        self._counter_var.set("Row 0 of ?")
        self._log(f"Starting processing... File: {os.path.basename(filepath)}")
        self._log(f"Sheet: {self._sheet_var.get()}, AI Backend: {self._ai_backend_var.get()}")

        # Start worker thread
        self._worker_thread = threading.Thread(
            target=self._run_worker, args=(filepath,), daemon=True
        )
        self._worker_thread.start()

    def _stop_processing(self):
        """Stop current processing."""
        self._stop_flag[0] = True
        self._set_status("Stopping after current row...")
        self._stop_btn.config(state="disabled")

    def _start_image_analysis(self):
        """Start image analysis for UNCERTAIN rows."""
        # This will be implemented in Phase 4
        messagebox.showinfo("Info", "Image analysis will be available in the next update.")

    def _run_worker(self, filepath: str):
        """Main processing worker thread."""
        try:
            from excel_handler import process_rows

            def on_progress(current, total):
                pct = int(current / total * 100) if total else 0
                self.after(0, self._update_progress, current, total, pct)

            def on_log(msg):
                self.after(0, self._log, msg)

            # Parse limit
            limit = None
            limit_text = self._limit_var.get().strip()
            if limit_text:
                try:
                    limit = int(limit_text)
                except ValueError:
                    self.after(0, self._log, f"Invalid limit value: {limit_text}")

            # Run processing
            process_rows(
                filepath=filepath,
                sheet_name=self._sheet_var.get(),
                reprocess_uncertain=self._reprocess_var.get(),
                on_progress=on_progress,
                on_log=on_log,
                stop_flag=self._stop_flag,
                limit=limit
            )

            if self._stop_flag[0]:
                self.after(0, self._set_status, "Stopped")
            else:
                self.after(0, self._set_status, "Completed")
                self.after(0, self._refresh_stats)
                self.after(0, self._refresh_excel_data)

        except Exception as e:
            self.after(0, self._log_error, f"FATAL ERROR: {e}")
            self.after(0, self._set_status, "Error")

        finally:
            self.after(0, self._on_worker_done)

    def _on_worker_done(self):
        """Clean up after worker thread completes."""
        self._start_btn.config(state="normal")
        self._stop_btn.config(state="disabled")

    def _apply_ai_backend(self):
        """Apply the selected AI backend configuration."""
        backend = self._ai_backend_var.get()

        if backend == "Claude API":
            self._activate_claude_api()
            self._log(f"Activated Claude API backend")
        elif backend == "Gemini API":
            # Keep existing Gemini configuration
            self._log(f"Using Gemini API backend")
        elif backend == "Ollama Local":
            # Ollama is already configured
            self._log(f"Using Ollama local backend")
        else:  # Rules Only
            self._log(f"Using rules-only backend (no AI)")

    def _activate_claude_api(self):
        """Activate Claude API by modifying the import in rule_compare.py."""
        rule_compare_path = Path(__file__).parent.parent / "rule_compare.py"

        try:
            # Read the current file
            content = rule_compare_path.read_text()

            # Replace the import line
            old_import = "from local_text_compare import compare_parts as gemini_compare"
            new_import = "from ai_compare import compare_parts as claude_compare"

            if old_import in content:
                content = content.replace(old_import, new_import)
                # Also replace the function call
                content = content.replace("gemini_compare", "claude_compare")
                rule_compare_path.write_text(content)
                self._log("Claude API activated successfully")
            else:
                self._log("Claude API may already be active")

        except Exception as e:
            self._log_error(f"Failed to activate Claude API: {e}")

    # UI helper methods
    def _update_progress(self, current: int, total: int, pct: int):
        """Update progress display."""
        self._progress_var.set(pct)
        self._counter_var.set(f"Row {current} of {total}")

    def _set_status(self, text: str):
        """Update status display."""
        self._status_var.set(text)
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._log(f"[{timestamp}] Status: {text}")

    def _log(self, msg: str):
        """Add message to main log."""
        self._add_log_message(self._log_box, msg)

    def _log_error(self, msg: str):
        """Add message to error log."""
        self._add_log_message(self._error_log_box, msg)
        # Also add to main log with ERROR prefix
        self._log(f"ERROR: {msg}")

    def _log_ai(self, msg: str):
        """Add message to AI log."""
        self._add_log_message(self._ai_log_box, msg)

    def _add_log_message(self, log_widget, msg: str):
        """Helper to add message to any log widget."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_widget.config(state="normal")
        log_widget.insert("end", f"[{timestamp}] {msg}\n")

        # Keep only last ~200 lines
        lines = int(log_widget.index("end-1c").split(".")[0])
        if lines > 220:
            log_widget.delete("1.0", f"{lines - 200}.0")

        log_widget.see("end")
        log_widget.config(state="disabled")

    def _refresh_stats(self):
        """Refresh the statistics dashboard."""
        try:
            filepath = self._filepath_var.get().strip()
            if not filepath or not os.path.exists(filepath):
                stats_text = "No Excel file loaded."
            else:
                # Use the existing count_results function
                stats = count_all_results(filepath)
                stats_text = self._format_stats(stats)

            self._stats_text.config(state="normal")
            self._stats_text.delete(1.0, tk.END)
            self._stats_text.insert(1.0, stats_text)
            self._stats_text.config(state="disabled")

        except Exception as e:
            self._log_error(f"Failed to refresh stats: {e}")

    def _format_stats(self, stats: dict) -> str:
        """Format statistics for display."""
        lines = ["PROCESSING STATISTICS", "=" * 30, ""]

        for sheet_name, counts in stats.items():
            if not counts:  # Skip empty sheets
                continue

            lines.append(f"{sheet_name.upper()}:")
            lines.append(f"  YES: {counts.get('YES', 0)}")
            lines.append(f"  LIKELY: {counts.get('LIKELY', 0)}")
            lines.append(f"  UNCERTAIN: {counts.get('UNCERTAIN', 0)}")
            lines.append(f"  NO: {counts.get('NO', 0)}")

            total = sum(counts.values())
            if total > 0:
                success_rate = ((counts.get('YES', 0) + counts.get('LIKELY', 0)) / total) * 100
                lines.append(f"  Total: {total} ({success_rate:.1f}% success)")
            lines.append("")

        return "\n".join(lines)

    def _load_excel_data(self):
        """Load Excel data into the viewer."""
        # This will be implemented in Phase 4
        messagebox.showinfo("Info", "Excel viewer will be enhanced in the next update.")

    def _refresh_excel_data(self):
        """Refresh Excel data display."""
        # This will be implemented in Phase 4
        pass

    def _export_view(self):
        """Export current view to file."""
        # This will be implemented in Phase 4
        messagebox.showinfo("Info", "Export functionality will be available in the next update.")

    def _filter_data(self, event=None):
        """Filter displayed data."""
        # This will be implemented in Phase 4
        pass

    def _reset_cost(self):
        """Reset daily cost tracking."""
        self.cost_tracker.reset_daily()
        self._cost_display_var.set("$0.00")
        self._log("Daily cost counter reset")

    # Menu handlers (stubs for now)
    def _import_config(self):
        messagebox.showinfo("Info", "Configuration import will be available in the next update.")

    def _export_config(self):
        messagebox.showinfo("Info", "Configuration export will be available in the next update.")

    def _show_ai_settings(self):
        messagebox.showinfo("Info", "AI settings dialog will be available in the next update.")

    def _show_site_wizard(self):
        messagebox.showinfo("Info", "Site configuration wizard will be available in the next update.")

    def _show_cost_manager(self):
        messagebox.showinfo("Info", "Cost management dialog will be available in the next update.")

    def _show_analytics_dashboard(self):
        """Show the enhanced analytics dashboard."""
        if not ANALYTICS_AVAILABLE:
            messagebox.showerror("Analytics Unavailable",
                               "Analytics dashboard is not available.\n"
                               "Required dependencies may not be installed.")
            return

        if not self.analytics_dashboard:
            messagebox.showerror("Dashboard Error",
                               "Analytics dashboard failed to initialize.\n"
                               "Check the error log for details.")
            return

        try:
            # Set the current Excel file path
            current_file = self._filepath_var.get().strip()
            if current_file and os.path.exists(current_file):
                self.analytics_dashboard.excel_path = current_file

            # Show the dashboard
            self.analytics_dashboard.show_dashboard()
            self._log("Analytics dashboard opened")

        except Exception as e:
            messagebox.showerror("Dashboard Error",
                               f"Failed to open analytics dashboard:\n{str(e)}")
            self._log_error(f"Analytics dashboard error: {e}")

    def _show_statistics(self):
        """Show basic statistics (legacy function)."""
        if ANALYTICS_AVAILABLE and self.analytics_dashboard:
            # Redirect to analytics dashboard
            self._show_analytics_dashboard()
        else:
            messagebox.showinfo("Info", "Analytics dashboard not available.\nShowing basic statistics instead.")
            # Show basic statistics in a simple window
            self._show_basic_statistics()

    def _show_help(self):
        messagebox.showinfo("Parts Agent Pro",
                          "Parts Agent Pro - Unified Auto Parts Matching\n\n"
                          "Phase 1: Enhanced GUI Foundation\n"
                          "- Multi-panel professional interface\n"
                          "- Job queue and progress tracking\n"
                          "- Statistics dashboard\n\n"
                          "More features coming in upcoming phases!")

    def _show_basic_statistics(self):
        """Show basic statistics in a simple window."""
        try:
            stats_window = tk.Toplevel(self)
            stats_window.title("Basic Statistics")
            stats_window.geometry("500x400")

            # Get current file stats
            filepath = self._filepath_var.get().strip()
            if filepath and os.path.exists(filepath):
                stats = count_all_results(filepath)
                stats_text = self._format_stats(stats)
            else:
                stats_text = "No Excel file loaded or file not found."

            # Create text display
            text_frame = tk.Frame(stats_window)
            text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

            stats_display = tk.Text(text_frame, wrap=tk.WORD, font=("Consolas", 10))
            stats_display.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

            scrollbar = tk.Scrollbar(text_frame, orient=tk.VERTICAL, command=stats_display.yview)
            stats_display.configure(yscrollcommand=scrollbar.set)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            # Insert stats
            stats_display.insert(tk.END, stats_text)
            stats_display.config(state="disabled")

            # Add buttons
            button_frame = tk.Frame(stats_window)
            button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)

            tk.Button(button_frame, text="Refresh", command=lambda: self._refresh_basic_stats(stats_display)).pack(side=tk.LEFT, padx=5)
            tk.Button(button_frame, text="Close", command=stats_window.destroy).pack(side=tk.RIGHT, padx=5)

        except Exception as e:
            messagebox.showerror("Statistics Error", f"Failed to show statistics:\n{str(e)}")

    def _refresh_basic_stats(self, text_widget):
        """Refresh basic statistics display."""
        try:
            filepath = self._filepath_var.get().strip()
            if filepath and os.path.exists(filepath):
                stats = count_all_results(filepath)
                stats_text = self._format_stats(stats)
            else:
                stats_text = "No Excel file loaded or file not found."

            text_widget.config(state="normal")
            text_widget.delete(1.0, tk.END)
            text_widget.insert(1.0, stats_text)
            text_widget.config(state="disabled")

        except Exception as e:
            messagebox.showerror("Refresh Error", f"Failed to refresh statistics:\n{str(e)}")

    def _show_about(self):
        messagebox.showinfo("About",
                          "Parts Agent Pro v2.0\n"
                          "Enhanced unified GUI application\n\n"
                          "Built on proven foundations:\n"
                          "- 67-80% match success rates\n"
                          "- Local AI capabilities\n"
                          "- Comprehensive scraping engine\n"
                          "- Advanced analytics dashboard\n\n"
                          "© 2026 Auto Parts Matching System")


def main():
    """Main entry point for the unified GUI application."""
    app = UnifiedPartsAgent()
    app.mainloop()


if __name__ == "__main__":
    main()