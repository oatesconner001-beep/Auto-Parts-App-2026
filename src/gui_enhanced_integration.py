"""
Enhanced GUI Integration - Phase 1 Implementation

Adds enhanced image analysis controls to the existing GUI system.
Provides safe access to the new enhanced comparison capabilities.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import subprocess
import os
from pathlib import Path

class EnhancedImageAnalysisFrame(ttk.LabelFrame):
    """Enhanced image analysis controls for the GUI"""

    def __init__(self, parent):
        super().__init__(parent, text="Enhanced Image Analysis (Phase 1)")

        self.parent = parent
        self.analysis_thread = None
        self.is_running = False

        self._build_enhanced_controls()

    def _build_enhanced_controls(self):
        """Build enhanced image analysis controls"""

        # Description
        desc_text = (
            "Enhanced system: SSIM + CLIP + improved thresholds\n"
            "Target: 74%+ UNCERTAIN→LIKELY upgrade rate (vs 67% baseline)\n"
            "Speed: ~30s per row (vs 14s baseline, but higher accuracy)"
        )

        desc_label = ttk.Label(self, text=desc_text, foreground="blue")
        desc_label.pack(pady=(5, 10))

        # Sheet selection
        sheet_frame = ttk.Frame(self)
        sheet_frame.pack(fill="x", pady=5)

        ttk.Label(sheet_frame, text="Sheet:").pack(side="left", padx=(5, 5))

        self.sheet_var = tk.StringVar(value="Anchor")
        sheet_combo = ttk.Combobox(
            sheet_frame,
            textvariable=self.sheet_var,
            values=["Anchor", "Dorman", "GMB", "SMP", "Four Seasons "],
            state="readonly",
            width=15
        )
        sheet_combo.pack(side="left", padx=(0, 10))

        # Limit controls
        ttk.Label(sheet_frame, text="Limit:").pack(side="left", padx=(10, 5))

        self.limit_var = tk.StringVar(value="5")
        limit_entry = ttk.Entry(sheet_frame, textvariable=self.limit_var, width=8)
        limit_entry.pack(side="left", padx=(0, 5))

        ttk.Label(sheet_frame, text="rows (for testing)").pack(side="left")

        # Mode selection
        mode_frame = ttk.Frame(self)
        mode_frame.pack(fill="x", pady=5)

        self.dry_run_var = tk.BooleanVar(value=True)
        dry_run_check = ttk.Checkbutton(
            mode_frame,
            text="Dry run (preview only, no Excel updates)",
            variable=self.dry_run_var
        )
        dry_run_check.pack(side="left", padx=(5, 0))

        # Control buttons
        button_frame = ttk.Frame(self)
        button_frame.pack(fill="x", pady=10)

        self.start_btn = ttk.Button(
            button_frame,
            text="Start Enhanced Analysis",
            command=self._start_enhanced_analysis,
            style="Accent.TButton"
        )
        self.start_btn.pack(side="left", padx=(5, 5))

        self.stop_btn = ttk.Button(
            button_frame,
            text="Stop",
            command=self._stop_analysis,
            state="disabled"
        )
        self.stop_btn.pack(side="left", padx=(5, 5))

        # Progress and status
        self.progress_var = tk.StringVar(value="Ready")
        progress_label = ttk.Label(self, textvariable=self.progress_var)
        progress_label.pack(pady=5)

        self.progress_bar = ttk.Progressbar(self, mode="indeterminate")
        self.progress_bar.pack(fill="x", padx=5, pady=5)

        # Results display
        results_frame = ttk.LabelFrame(self, text="Last Run Results")
        results_frame.pack(fill="both", expand=True, pady=5)

        self.results_text = tk.Text(results_frame, height=8, wrap="word")
        self.results_text.pack(fill="both", expand=True, padx=5, pady=5)

        # Scrollbar for results
        scrollbar = ttk.Scrollbar(results_frame, command=self.results_text.yview)
        self.results_text.config(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")

    def _start_enhanced_analysis(self):
        """Start enhanced image analysis in background"""

        if self.is_running:
            messagebox.showwarning("Analysis Running", "Enhanced analysis is already running!")
            return

        # Validate inputs
        try:
            limit = int(self.limit_var.get())
            if limit < 1 or limit > 100:
                raise ValueError("Limit must be between 1 and 100")
        except ValueError as e:
            messagebox.showerror("Invalid Input", f"Invalid limit: {e}")
            return

        sheet = self.sheet_var.get()
        dry_run = self.dry_run_var.get()

        # Update UI state
        self.is_running = True
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.progress_bar.start()
        self.progress_var.set(f"Starting enhanced analysis on {sheet}...")
        self.results_text.delete(1.0, tk.END)
        self.results_text.insert(tk.END, f"Starting enhanced image analysis...\\n")
        self.results_text.insert(tk.END, f"Sheet: {sheet}\\n")
        self.results_text.insert(tk.END, f"Limit: {limit} rows\\n")
        self.results_text.insert(tk.END, f"Mode: {'Dry run' if dry_run else 'Live updates'}\\n\\n")

        # Start analysis thread
        self.analysis_thread = threading.Thread(
            target=self._run_enhanced_analysis,
            args=(sheet, limit, dry_run),
            daemon=True
        )
        self.analysis_thread.start()

    def _run_enhanced_analysis(self, sheet, limit, dry_run):
        """Run enhanced analysis in background thread"""

        try:
            # Build command
            script_path = Path(__file__).parent / "run_enhanced_image_analysis.py"

            cmd = [
                "uv", "run", "python", str(script_path),
                sheet, "--limit", str(limit)
            ]

            if dry_run:
                cmd.append("--dry-run")

            # Set environment
            env = os.environ.copy()
            env["PATH"] = f"{env['PATH']}:/c/Users/Owner/.local/bin"

            # Run analysis
            self.progress_var.set(f"Running enhanced analysis...")

            result = subprocess.run(
                cmd,
                cwd=Path(__file__).parent.parent,
                capture_output=True,
                text=True,
                env=env,
                timeout=600  # 10 minute timeout
            )

            # Process results
            if result.returncode == 0:
                self._analysis_completed(result.stdout, success=True)
            else:
                self._analysis_completed(result.stderr, success=False)

        except subprocess.TimeoutExpired:
            self._analysis_completed("Analysis timed out after 10 minutes", success=False)
        except Exception as e:
            self._analysis_completed(f"Analysis failed: {e}", success=False)

    def _analysis_completed(self, output, success=True):
        """Handle analysis completion"""

        def update_ui():
            self.is_running = False
            self.start_btn.config(state="normal")
            self.stop_btn.config(state="disabled")
            self.progress_bar.stop()

            if success:
                self.progress_var.set("Enhanced analysis completed successfully!")

                # Parse results from output
                lines = output.split('\\n')
                for line in lines:
                    self.results_text.insert(tk.END, line + "\\n")

                # Extract key metrics
                upgrade_lines = [l for l in lines if "Upgrade to LIKELY:" in l]
                if upgrade_lines:
                    self.results_text.insert(tk.END, "\\n=== KEY RESULTS ===\\n")
                    self.results_text.insert(tk.END, upgrade_lines[0] + "\\n")

                success_lines = [l for l in lines if "Success rate:" in l]
                if success_lines:
                    self.results_text.insert(tk.END, success_lines[0] + "\\n")

            else:
                self.progress_var.set("Enhanced analysis failed!")
                self.results_text.insert(tk.END, f"\\nERROR:\\n{output}")

            self.results_text.see(tk.END)

        # Update UI from main thread
        self.parent.after(0, update_ui)

    def _stop_analysis(self):
        """Stop running analysis"""
        self.is_running = False
        self.progress_var.set("Stopping analysis...")

        # Note: subprocess termination would need more complex handling
        # For now, just update UI state
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.progress_bar.stop()
        self.progress_var.set("Analysis stopped by user")

def add_enhanced_controls_to_gui(root_window):
    """Add enhanced image analysis controls to existing GUI"""

    # Create enhanced frame
    enhanced_frame = EnhancedImageAnalysisFrame(root_window)
    enhanced_frame.pack(fill="both", expand=True, padx=8, pady=4)

    return enhanced_frame

if __name__ == "__main__":
    # Test the enhanced controls
    root = tk.Tk()
    root.title("Enhanced Image Analysis - Test")
    root.geometry("800x600")

    enhanced_frame = EnhancedImageAnalysisFrame(root)
    enhanced_frame.pack(fill="both", expand=True, padx=10, pady=10)

    root.mainloop()