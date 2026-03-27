"""
Parts Agent GUI — tkinter interface for the Excel processing pipeline.
"""

import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext
import threading
import time
import os


DEFAULT_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "FISHER SKP INTERCHANGE 20260302.xlsx",
)


class PartsAgentApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Parts Agent — Anchor vs SKP Matcher")
        self.resizable(True, True)
        self.minsize(700, 480)

        self._stop_flag = [False]
        self._worker_thread = None

        self._build_ui()

        # Pre-fill the file path if the default exists
        if os.path.exists(DEFAULT_FILE):
            self._filepath_var.set(DEFAULT_FILE)

    # ------------------------------------------------------------------ UI build

    def _build_ui(self):
        pad = {"padx": 8, "pady": 4}

        # ── File selection ──────────────────────────────────────────────
        file_frame = ttk.LabelFrame(self, text="Excel File")
        file_frame.pack(fill="x", **pad)

        self._filepath_var = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self._filepath_var, width=70).pack(
            side="left", expand=True, fill="x", padx=(6, 2), pady=4
        )
        ttk.Button(file_frame, text="Browse…", command=self._browse).pack(
            side="left", padx=(2, 6), pady=4
        )

        # ── Controls ────────────────────────────────────────────────────
        ctrl_frame = ttk.Frame(self)
        ctrl_frame.pack(fill="x", **pad)

        # Sheet selector
        ttk.Label(ctrl_frame, text="Sheet:").pack(side="left", padx=(0, 2))
        self._sheet_var = tk.StringVar(value="Anchor")
        sheet_combo = ttk.Combobox(
            ctrl_frame, textvariable=self._sheet_var, width=12,
            values=["Anchor", "Dorman", "GMB", "SMP", "Four Seasons "],
            state="readonly",
        )
        sheet_combo.pack(side="left", padx=(0, 8))

        # Reprocess uncertain checkbox
        self._reprocess_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            ctrl_frame, text="Re-process UNCERTAIN", variable=self._reprocess_var
        ).pack(side="left", padx=(0, 12))

        self._start_btn = ttk.Button(
            ctrl_frame, text="Start Processing", command=self._start, width=20
        )
        self._start_btn.pack(side="left", padx=(0, 6))

        self._stop_btn = ttk.Button(
            ctrl_frame, text="Stop", command=self._stop, state="disabled", width=10
        )
        self._stop_btn.pack(side="left", padx=(0, 20))

        self._status_var = tk.StringVar(value="Idle")
        ttk.Label(ctrl_frame, textvariable=self._status_var, foreground="#555").pack(
            side="left"
        )

        # ── Progress ────────────────────────────────────────────────────
        prog_frame = ttk.Frame(self)
        prog_frame.pack(fill="x", **pad)

        self._progress_var = tk.IntVar(value=0)
        self._progress_bar = ttk.Progressbar(
            prog_frame,
            variable=self._progress_var,
            maximum=100,
            length=500,
        )
        self._progress_bar.pack(side="left", expand=True, fill="x", padx=(0, 8))

        self._counter_var = tk.StringVar(value="Row 0 of 0")
        ttk.Label(prog_frame, textvariable=self._counter_var, width=18).pack(side="left")

        # ── Log window ──────────────────────────────────────────────────
        log_frame = ttk.LabelFrame(self, text="Activity Log")
        log_frame.pack(fill="both", expand=True, **pad)

        self._log_box = scrolledtext.ScrolledText(
            log_frame,
            height=16,
            state="disabled",
            font=("Consolas", 9),
            wrap="word",
        )
        self._log_box.pack(fill="both", expand=True, padx=4, pady=4)

    # ------------------------------------------------------------------ Callbacks

    def _browse(self):
        path = filedialog.askopenfilename(
            title="Select Excel file",
            filetypes=[("Excel files", "*.xlsx *.xlsm"), ("All files", "*.*")],
        )
        if path:
            self._filepath_var.set(path)

    def _start(self):
        filepath = self._filepath_var.get().strip()
        if not filepath:
            self._log("Please select an Excel file first.")
            return
        if not os.path.exists(filepath):
            self._log(f"File not found: {filepath}")
            return

        self._stop_flag[0] = False
        self._start_btn.config(state="disabled")
        self._stop_btn.config(state="normal")
        self._set_status("Running…")
        self._progress_var.set(0)
        self._counter_var.set("Row 0 of ?")
        self._log(f"Starting… file: {os.path.basename(filepath)}")

        self._worker_thread = threading.Thread(
            target=self._run_worker,
            args=(filepath,),
            daemon=True,
        )
        self._worker_thread.start()

    def _stop(self):
        self._stop_flag[0] = True
        self._set_status("Stopping after current row…")
        self._stop_btn.config(state="disabled")

    def _run_worker(self, filepath: str):
        try:
            from excel_handler import process_rows

            self._total = None  # will be set on first progress call

            def on_progress(current, total):
                self._total = total
                pct = int(current / total * 100) if total else 0
                self.after(0, self._update_progress, current, total, pct)

            def on_log(msg):
                self.after(0, self._log, msg)

            process_rows(
                filepath,
                sheet_name=self._sheet_var.get(),
                reprocess_uncertain=self._reprocess_var.get(),
                on_progress=on_progress,
                on_log=on_log,
                stop_flag=self._stop_flag,
            )

            if self._stop_flag[0]:
                self.after(0, self._set_status, "Stopped")
            else:
                self.after(0, self._set_status, "Done ✓")

        except Exception as e:
            self.after(0, self._log, f"FATAL ERROR: {e}")
            self.after(0, self._set_status, "Error")

        finally:
            self.after(0, self._on_worker_done)

    def _on_worker_done(self):
        self._start_btn.config(state="normal")
        self._stop_btn.config(state="disabled")

    # ------------------------------------------------------------------ UI helpers

    def _update_progress(self, current: int, total: int, pct: int):
        self._progress_var.set(pct)
        self._counter_var.set(f"Row {current} of {total}")

    def _set_status(self, text: str):
        self._status_var.set(text)

    def _log(self, msg: str):
        self._log_box.config(state="normal")
        self._log_box.insert("end", msg + "\n")
        # Keep only last ~200 lines
        lines = int(self._log_box.index("end-1c").split(".")[0])
        if lines > 220:
            self._log_box.delete("1.0", f"{lines - 200}.0")
        self._log_box.see("end")
        self._log_box.config(state="disabled")


if __name__ == "__main__":
    app = PartsAgentApp()
    app.mainloop()
