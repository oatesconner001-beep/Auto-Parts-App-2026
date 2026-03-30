#!/usr/bin/env python3
"""
Multi-Site Management Tab for Parts Agent GUI
Integrates with existing tkinter interface
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import json
import sys
from pathlib import Path
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from scrapers.multi_site_manager import MultiSiteScraperManager
    from database.db_manager import DatabaseManager
except ImportError as e:
    print(f"Import error: {e}")
    # Graceful fallback if modules not available
    MultiSiteScraperManager = None
    DatabaseManager = None


class MultiSiteTab:
    """Multi-site management tab for the main GUI"""

    def __init__(self, parent_notebook: ttk.Notebook):
        """Initialize multi-site tab

        Args:
            parent_notebook: Parent notebook widget
        """
        self.parent = parent_notebook

        # Create multi-site frame
        self.frame = ttk.Frame(parent_notebook)
        parent_notebook.add(self.frame, text="Multi-Site")

        # Initialize components
        self.manager = None
        self.db_manager = None
        self._init_managers()
        self._create_widgets()
        self._load_site_status()

    def _init_managers(self):
        """Initialize manager instances if available"""
        try:
            if MultiSiteScraperManager and DatabaseManager:
                self.db_manager = DatabaseManager()
                self.manager = MultiSiteScraperManager(self.db_manager)
            else:
                print("Multi-site managers not available")
        except Exception as e:
            print(f"Failed to initialize multi-site managers: {e}")

    def _create_widgets(self):
        """Create and layout GUI widgets"""
        # Title
        title_label = ttk.Label(self.frame, text="Multi-Site Parts Scraping",
                               font=('Arial', 14, 'bold'))
        title_label.pack(pady=10)

        # Main container with two columns
        main_container = ttk.Frame(self.frame)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # Left column - Site management
        left_frame = ttk.LabelFrame(main_container, text="Site Management", padding="10")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        # Site status display
        self.site_tree = ttk.Treeview(left_frame, columns=('Status', 'Delay', 'Success Rate'),
                                     height=8, show='tree headings')
        self.site_tree.heading('#0', text='Site')
        self.site_tree.heading('Status', text='Status')
        self.site_tree.heading('Delay', text='Delay (s)')
        self.site_tree.heading('Success Rate', text='Success %')

        # Configure column widths
        self.site_tree.column('#0', width=120)
        self.site_tree.column('Status', width=80)
        self.site_tree.column('Delay', width=70)
        self.site_tree.column('Success Rate', width=80)

        self.site_tree.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Site control buttons
        site_buttons_frame = ttk.Frame(left_frame)
        site_buttons_frame.pack(fill=tk.X)

        self.refresh_sites_btn = ttk.Button(site_buttons_frame, text="Refresh Sites",
                                           command=self._load_site_status)
        self.refresh_sites_btn.pack(side=tk.LEFT, padx=(0, 5))

        self.toggle_site_btn = ttk.Button(site_buttons_frame, text="Toggle Site",
                                         command=self._toggle_selected_site)
        self.toggle_site_btn.pack(side=tk.LEFT, padx=5)

        # Right column - Scraping operations
        right_frame = ttk.LabelFrame(main_container, text="Multi-Site Scraping", padding="10")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))

        # Part search inputs
        search_frame = ttk.Frame(right_frame)
        search_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(search_frame, text="Part Number:").grid(row=0, column=0, sticky=tk.W)
        self.part_number_entry = ttk.Entry(search_frame, width=20)
        self.part_number_entry.grid(row=0, column=1, padx=5, sticky=tk.W)

        ttk.Label(search_frame, text="Brand:").grid(row=1, column=0, sticky=tk.W, pady=(5, 0))
        self.brand_entry = ttk.Entry(search_frame, width=20)
        self.brand_entry.grid(row=1, column=1, padx=5, pady=(5, 0), sticky=tk.W)

        # Site selection
        ttk.Label(search_frame, text="Sites to Search:").grid(row=2, column=0, sticky=tk.NW, pady=(10, 0))

        sites_frame = ttk.Frame(search_frame)
        sites_frame.grid(row=2, column=1, padx=5, pady=(10, 0), sticky=tk.W)

        self.site_vars = {}
        self._create_site_checkboxes(sites_frame)

        # Search button
        self.search_btn = ttk.Button(search_frame, text="Search All Sites",
                                    command=self._start_multi_site_search)
        self.search_btn.grid(row=3, column=0, columnspan=2, pady=10)

        # Progress bar
        self.progress_var = tk.StringVar(value="Ready")
        progress_label = ttk.Label(right_frame, textvariable=self.progress_var)
        progress_label.pack()

        self.progress_bar = ttk.Progressbar(right_frame, mode='indeterminate')
        self.progress_bar.pack(fill=tk.X, pady=5)

        # Results display
        results_frame = ttk.LabelFrame(right_frame, text="Results", padding="5")
        results_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        self.results_text = scrolledtext.ScrolledText(results_frame, height=15, width=50)
        self.results_text.pack(fill=tk.BOTH, expand=True)

        # Pre-fill with test data
        self.part_number_entry.insert(0, "3217")
        self.brand_entry.insert(0, "ANCHOR")

    def _create_site_checkboxes(self, parent_frame):
        """Create checkboxes for site selection

        Args:
            parent_frame: Parent frame for checkboxes
        """
        default_sites = ['RockAuto', 'PartsGeek', 'ACDelco', 'Dorman', 'Moog']

        row = 0
        col = 0
        for site in default_sites:
            var = tk.BooleanVar(value=(site == 'RockAuto'))  # Only RockAuto enabled by default
            self.site_vars[site] = var

            cb = ttk.Checkbutton(parent_frame, text=site, variable=var)
            cb.grid(row=row, column=col, sticky=tk.W, padx=5)

            col += 1
            if col > 1:  # Two columns
                col = 0
                row += 1

    def _load_site_status(self):
        """Load and display site status information"""
        if not self.manager:
            self._insert_result("Multi-site manager not available")
            return

        try:
            # Clear existing items
            for item in self.site_tree.get_children():
                self.site_tree.delete(item)

            # Get site performance data
            performance_data = self.db_manager.get_site_performance()
            configs = self.manager.site_configs

            # Display each site
            for site_name, config in configs.items():
                status = "Active" if config.get('is_active', False) else "Inactive"
                if config.get('status') == 'blocked':
                    status = "Blocked"

                delay = config.get('rate_limit_delay', 0)

                # Find performance data for this site
                perf = next((p for p in performance_data if p['site_name'] == site_name), None)
                success_rate = f"{perf['success_rate']:.1f}" if perf and perf.get('success_rate') else "N/A"

                self.site_tree.insert('', tk.END, text=site_name,
                                     values=(status, delay, success_rate))

        except Exception as e:
            self._insert_result(f"Error loading site status: {e}")

    def _toggle_selected_site(self):
        """Toggle active status of selected site"""
        selection = self.site_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a site to toggle")
            return

        if not self.db_manager:
            messagebox.showerror("Error", "Database manager not available")
            return

        try:
            item = selection[0]
            site_name = self.site_tree.item(item)['text']

            # Don't allow toggling blocked sites
            current_config = self.manager.site_configs.get(site_name, {})
            if current_config.get('status') == 'blocked':
                messagebox.showwarning("Warning",
                    f"{site_name} requires stealth bypass testing before activation — see src/scrapers/ for scraper")
                return

            # Toggle active status
            current_active = current_config.get('is_active', False)
            new_active = not current_active

            success = self.db_manager.update_site_config(
                site_name, is_active=new_active
            )

            if success:
                # Reload site configurations
                self.manager._load_site_configs()
                self._load_site_status()
                status = "activated" if new_active else "deactivated"
                self._insert_result(f"{site_name} {status}")
            else:
                messagebox.showerror("Error", f"Failed to toggle {site_name}")

        except Exception as e:
            messagebox.showerror("Error", f"Error toggling site: {e}")

    def _start_multi_site_search(self):
        """Start multi-site search in background thread"""
        part_number = self.part_number_entry.get().strip()
        brand = self.brand_entry.get().strip()

        if not part_number or not brand:
            messagebox.showwarning("Warning", "Please enter both part number and brand")
            return

        if not self.manager:
            messagebox.showerror("Error", "Multi-site manager not available")
            return

        # Get selected sites
        selected_sites = [site for site, var in self.site_vars.items() if var.get()]
        if not selected_sites:
            messagebox.showwarning("Warning", "Please select at least one site to search")
            return

        # Disable controls and start progress
        self.search_btn.config(state='disabled')
        self.progress_bar.start()
        self.progress_var.set("Searching...")

        # Start search in background thread
        search_thread = threading.Thread(
            target=self._perform_multi_site_search,
            args=(part_number, brand, selected_sites),
            daemon=True
        )
        search_thread.start()

    def _perform_multi_site_search(self, part_number: str, brand: str, sites: list):
        """Perform multi-site search in background

        Args:
            part_number: Part number to search
            brand: Brand name
            sites: List of sites to search
        """
        try:
            self._insert_result(f"\n=== Multi-Site Search: {brand} {part_number} ===")
            self._insert_result(f"Searching {len(sites)} sites: {', '.join(sites)}")

            # Perform the search
            results = self.manager.scrape_part_multi_site(
                part_number=part_number,
                brand=brand,
                sites=sites,
                store_results=True
            )

            # Update UI with results
            self._display_search_results(results)

        except Exception as e:
            self._insert_result(f"Search error: {e}")

        finally:
            # Re-enable controls
            self._search_completed()

    def _display_search_results(self, results: dict):
        """Display search results in the results area

        Args:
            results: Search results from multi-site manager
        """
        summary = results['summary']
        self._insert_result(f"\nResults Summary:")
        self._insert_result(f"  Sites searched: {summary['total_sites']}")
        self._insert_result(f"  Successful: {summary['successful_sites']}")
        self._insert_result(f"  Found on: {summary['found_on_sites']} sites")

        # Display individual site results
        self._insert_result(f"\nSite Details:")
        for site_name, site_result in results['sites'].items():
            self._insert_result(f"\n{site_name}:")
            self._insert_result(f"  Success: {site_result.get('success', False)}")
            self._insert_result(f"  Found: {site_result.get('found', False)}")

            if site_result.get('found'):
                self._insert_result(f"  Category: {site_result.get('category', 'N/A')}")
                price = site_result.get('price', 'N/A')
                self._insert_result(f"  Price: {price}")
                oem_count = len(site_result.get('oem_refs', []))
                self._insert_result(f"  OEM References: {oem_count}")

            if site_result.get('error'):
                self._insert_result(f"  Error: {site_result['error']}")

        # Show part summary if available
        try:
            summary_data = self.manager.get_multi_site_summary(
                results['part_number'], results['brand']
            )

            if 'error' not in summary_data:
                self._insert_result(f"\nPart Summary:")
                price_range = summary_data['price_range']
                if price_range['count'] > 0:
                    self._insert_result(f"  Price Range: ${price_range['min']:.2f} - ${price_range['max']:.2f}")

                oem_count = len(summary_data['oem_references'])
                if oem_count > 0:
                    self._insert_result(f"  Total OEM References: {oem_count}")

        except Exception as e:
            self._insert_result(f"  Summary error: {e}")

    def _search_completed(self):
        """Re-enable controls after search completion"""
        # Schedule UI updates on main thread
        self.frame.after(0, self._reset_search_ui)

    def _reset_search_ui(self):
        """Reset search UI to ready state"""
        self.progress_bar.stop()
        self.progress_var.set("Search completed")
        self.search_btn.config(state='normal')

        # Refresh site status to show updated success rates
        self._load_site_status()

    def _insert_result(self, text: str):
        """Insert text into results display thread-safely

        Args:
            text: Text to insert
        """
        # Schedule text insertion on main thread
        self.frame.after(0, lambda: self._do_insert_result(text))

    def _do_insert_result(self, text: str):
        """Actually insert text into results display

        Args:
            text: Text to insert
        """
        self.results_text.insert(tk.END, text + "\n")
        self.results_text.see(tk.END)


def test_multi_site_tab():
    """Test multi-site tab standalone"""
    root = tk.Tk()
    root.title("Multi-Site Tab Test")
    root.geometry("800x600")

    notebook = ttk.Notebook(root)
    notebook.pack(fill=tk.BOTH, expand=True)

    # Create multi-site tab
    multi_site_tab = MultiSiteTab(notebook)

    root.mainloop()


if __name__ == "__main__":
    test_multi_site_tab()