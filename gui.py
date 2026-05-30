"""
gui.py — Graphical User Interface for SimGenerator

Provides a comprehensive GUI for scenario generation, visualization, and editing.
Built with Tkinter — no external dependencies required.

Layout
------
Title header + [? Help] button
  Tab 1 "Generate"  — parameters form + progress log
  Tab 2 "Scenarios" — list | details (top), editable table (bottom)
Status bar
"""

import tkinter as tk
from tkinter import ttk, filedialog
import threading
import os
import configparser
from datetime import datetime
from typing import List, Optional

from models import ScenarioConfig, Scenario, GapConfiguration
from generator import ScenarioGenerator
from csv_writer import CSVWriter


# ─────────────────────────────────────────────────────────────────────────────
# Tooltip helper (floating notes on hover)
# ─────────────────────────────────────────────────────────────────────────────

class Tooltip:
    """Simple tooltip that appears on hover."""

    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        self.id = None
        self.x = self.y = 0
        widget.bind("<Enter>", self._on_enter)
        widget.bind("<Leave>", self._on_leave)

    def _on_enter(self, event=None):
        """Show tooltip on mouse enter."""
        if self.tipwindow or not self.text:
            return
        x = self.widget.winfo_rootx() + self.widget.winfo_width() + 5
        y = self.widget.winfo_rooty()
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, background="#ffffcc", relief=tk.SOLID,
                        borderwidth=1, font=("Helvetica", 9), wraplength=300, justify=tk.LEFT)
        label.pack(ipadx=4, ipady=3)

    def _on_leave(self, event=None):
        """Hide tooltip on mouse leave."""
        if self.tipwindow:
            self.tipwindow.destroy()
            self.tipwindow = None


# ─────────────────────────────────────────────────────────────────────────────
# Main application class
# ─────────────────────────────────────────────────────────────────────────────

class SimGeneratorGUI:
    """Main GUI application for SimGenerator."""

    # Column IDs must match the CSV header exactly.
    CSV_COLUMNS = (
        "Time_s",
        "Truck1_Velocity_kph",
        "Truck1_Event",
        "Truck2_Image_Event",
        "Truck3_Image_Event",
        "Notes",
    )
    CSV_HEADINGS = (
        "Time (s)",
        "Velocity (kph)",
        "T1 Event",
        "T2 Image",
        "T3 Image",
        "Notes",
    )
    # Column widths in pixels (Notes gets remaining space)
    CSV_COL_WIDTHS = (70, 100, 120, 90, 90, 200)

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("SimGenerator — Convoy Scenario Generator")
        self.root.geometry("1100x760")
        self.root.minsize(900, 620)

        # ── Settings file ────────────────────────────────────────────
        self.settings_file = os.path.join(os.path.dirname(__file__), ".simgen_settings.ini")

        # ── Application state ────────────────────────────────────────
        self.scenarios: List[Scenario] = []
        self.scenario_paths: List[str] = []   # parallel list — saved file path per scenario
        self.current_scenario_index: int = -1
        self.generation_running: bool = False
        self.stop_signal: threading.Event = threading.Event()
        self.pause_event: threading.Event = threading.Event()  # Set when paused, cleared when resuming

        # In-cell editor state
        self._cell_editor: Optional[tk.Entry] = None
        self._edit_row_id: Optional[str] = None
        self._edit_col_name: Optional[str] = None

        # Parameters file constraint widgets (initialized in _build_generate_tab)
        self.var_params_file: Optional[tk.StringVar] = None
        self.var_max_velocity: Optional[tk.DoubleVar] = None
        self.var_max_acceleration: Optional[tk.DoubleVar] = None

        # ENH-07: Gap configuration UI widgets (initialized in _build_generate_tab)
        self.var_gap1_mode: Optional[tk.StringVar] = None
        self.var_gap2_mode: Optional[tk.StringVar] = None
        self.var_gap1_value: Optional[tk.DoubleVar] = None
        self.var_gap1_min: Optional[tk.DoubleVar] = None
        self.var_gap1_max: Optional[tk.DoubleVar] = None
        self.var_gap2_value: Optional[tk.DoubleVar] = None
        self.var_gap2_min: Optional[tk.DoubleVar] = None
        self.var_gap2_max: Optional[tk.DoubleVar] = None
        self.gap1_spinbox: Optional[ttk.Spinbox] = None
        self.gap1_range_frame: Optional[ttk.Frame] = None
        self.gap2_spinbox: Optional[ttk.Spinbox] = None
        self.gap2_range_frame: Optional[ttk.Frame] = None

        # ── Build UI ─────────────────────────────────────────────────
        self._setup_styles()
        self._create_menu()
        self._create_header()
        self._create_notebook()
        self._create_statusbar()

        # ── Load settings ────────────────────────────────────────────
        self._load_settings()

        # ── Save settings on close ────────────────────────────────────
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)

    # ═════════════════════════════════════════════════════════════════════════
    # Setup helpers
    # ═════════════════════════════════════════════════════════════════════════

    def _setup_styles(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Title.TLabel",   font=("Helvetica", 14, "bold"))
        style.configure("Accent.TButton", font=("Helvetica", 10, "bold"))
        style.configure("Hint.TLabel",    foreground="#666666")

        # ENH-08: Configure Treeview with zebra striping (alternating row colors)
        style.configure("Treeview",
                       rowheight=22,  # Slightly taller rows for better separation
                       relief="flat",
                       borderwidth=0)
        style.map("Treeview",
                 background=[("selected", "#0078d7")],
                 foreground=[("selected", "white")])

        # Zebra striping: alternating background colors for even/odd rows
        style.configure("TreenodeEven.Treeview", background="#f8f8f8")
        style.configure("TreenodeOdd.Treeview",  background="#ffffff")
        style.map("TreenodeEven.Treeview",
                 background=[("selected", "#0078d7")],
                 foreground=[("selected", "white")])
        style.map("TreenodeOdd.Treeview",
                 background=[("selected", "#0078d7")],
                 foreground=[("selected", "white")])

    def _create_menu(self) -> None:
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(
            label="Open Scenarios from Folder…",
            command=self._open_scenarios_folder,
        )
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Help…", command=self._show_help)
        help_menu.add_command(label="About", command=self._show_about)

    def _create_header(self) -> None:
        """Application title bar with inline Help button."""
        bar = ttk.Frame(self.root, padding=(10, 7, 10, 5))
        bar.pack(fill=tk.X)

        ttk.Label(
            bar,
            text="SimGenerator — Convoy Scenario Generator",
            style="Title.TLabel",
        ).pack(side=tk.LEFT)

        ttk.Button(bar, text="? Help", command=self._show_help).pack(
            side=tk.RIGHT, padx=4
        )

        ttk.Separator(self.root, orient=tk.HORIZONTAL).pack(fill=tk.X)

    def _create_notebook(self) -> None:
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)

        self.tab_generate  = ttk.Frame(self.notebook)
        self.tab_scenarios = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_generate,  text="  Generate  ")
        self.notebook.add(self.tab_scenarios, text="  Scenarios  ")

        self._build_generate_tab()
        self._build_scenarios_tab()

    def _create_statusbar(self) -> None:
        self.statusbar = ttk.Label(
            self.root, text="Ready", relief=tk.SUNKEN, anchor=tk.W, padding=(6, 2)
        )
        self.statusbar.pack(side=tk.BOTTOM, fill=tk.X)

    # ═════════════════════════════════════════════════════════════════════════
    # Tab 1 — Generate (merged Parameters + Progress)
    # ═════════════════════════════════════════════════════════════════════════

    def _build_generate_tab(self) -> None:
        tab = self.tab_generate

        # ── Two-column layout: Parameters (left) + Output preview (right) ─
        params_container = ttk.Frame(tab)
        params_container.pack(fill=tk.BOTH, expand=True, padx=8, pady=(8, 4))
        params_container.columnconfigure(0, weight=1)  # Left column — parameters
        params_container.columnconfigure(1, weight=0)  # Right column — output preview (fixed width)
        params_container.rowconfigure(0, weight=1)

        # ── Parameters frame (LEFT) ──────────────────────────────────
        params = ttk.LabelFrame(params_container, text="Parameters", padding=12)
        params.grid(row=0, column=0, sticky=tk.NSEW, padx=(0, 8), pady=0)
        params.columnconfigure(1, weight=1)

        # Simple numeric rows
        self._param_row(params, 0, "Scenario Duration (s):",       "var_duration",   tk.DoubleVar, 120.0)
        self._param_row(params, 1, "Maximum Events:",               "var_max_events", tk.IntVar,    5)
        self._param_row(params, 2, "Minimum Event Separation (s):", "var_min_sep",    tk.DoubleVar, 5.0)
        self._param_row(params, 3, "Number of Scenarios:",          "var_count",      tk.IntVar,    10)

        # Seed row with "?" helper
        seed_label_frame = ttk.Frame(params)
        seed_label_frame.grid(row=4, column=0, sticky=tk.W, pady=(6, 0))
        ttk.Label(seed_label_frame, text="Random Seed:").pack(side=tk.LEFT)
        seed_help = tk.Label(seed_label_frame, text="?", font=("Helvetica", 10, "bold"),
                            foreground="#0078d7", cursor="hand2")
        seed_help.pack(side=tk.LEFT, padx=(4, 0))
        Tooltip(seed_help, "Any integer, e.g. 42. Same seed + same settings → identical scenarios every run. Leave blank for a fresh random batch each time.")

        self.var_seed = tk.StringVar(value="")
        ttk.Entry(params, textvariable=self.var_seed, width=14).grid(
            row=4, column=1, sticky=tk.W, pady=(6, 0)
        )

        # ── Parameters File browser (row 5) with "?" helper ──────────
        pf_label_frame = ttk.Frame(params)
        pf_label_frame.grid(row=5, column=0, sticky=tk.W, pady=(8, 0))
        ttk.Label(pf_label_frame, text="Parameters File:").pack(side=tk.LEFT)
        pf_help = tk.Label(pf_label_frame, text="?", font=("Helvetica", 10, "bold"),
                          foreground="#0078d7", cursor="hand2")
        pf_help.pack(side=tk.LEFT, padx=(4, 0))
        Tooltip(pf_help, "Browse a parameters CSV (same format as parameters_3.csv) to auto-fill the values above. You can also edit them manually. These are used as hard constraints on Truck 1 velocity generation.")

        pf_frame = ttk.Frame(params)
        pf_frame.grid(row=5, column=1, sticky=tk.EW)
        pf_frame.columnconfigure(1, weight=1)
        self.var_params_file = tk.StringVar(value="")
        ttk.Button(
            pf_frame, text="Browse…", command=self._browse_parameters_file
        ).grid(row=0, column=0, padx=(0, 6))
        ttk.Label(
            pf_frame, textvariable=self.var_params_file,
            style="Hint.TLabel", wraplength=450,
        ).grid(row=0, column=1, sticky=tk.EW)

        # Max Velocity + Max Acceleration (row 6) — editable, populated from file
        constraint_frame = ttk.Frame(params)
        constraint_frame.grid(row=6, column=0, columnspan=2, sticky=tk.EW, pady=(4, 0))
        self.var_max_velocity     = tk.DoubleVar(value=60.0)
        self.var_max_acceleration = tk.DoubleVar(value=10.0)
        ttk.Label(constraint_frame, text="Max Velocity (kph):").grid(
            row=0, column=0, sticky=tk.W, padx=(0, 4)
        )
        ttk.Spinbox(
            constraint_frame, from_=1, to=300,
            textvariable=self.var_max_velocity, width=8, format="%.1f",
        ).grid(row=0, column=1, sticky=tk.W, padx=(0, 20))
        ttk.Label(constraint_frame, text="Max Acceleration (m/s²):").grid(
            row=0, column=2, sticky=tk.W, padx=(0, 4)
        )
        ttk.Spinbox(
            constraint_frame, from_=0.1, to=20,
            textvariable=self.var_max_acceleration, width=8, format="%.2f",
        ).grid(row=0, column=3, sticky=tk.W)

        # Output root folder with "?" helper
        output_label_frame = ttk.Frame(params)
        output_label_frame.grid(row=7, column=0, sticky=tk.W, pady=4)
        ttk.Label(output_label_frame, text="Output Root Folder:").pack(side=tk.LEFT)
        output_help = tk.Label(output_label_frame, text="?", font=("Helvetica", 10, "bold"),
                              foreground="#0078d7", cursor="hand2")
        output_help.pack(side=tk.LEFT, padx=(4, 0))
        Tooltip(output_help, "Each run is saved in a new ddmmyyyy_hhmm sub-folder here. Leave blank to use the Scene_Gen folder in the current directory.")

        folder_frame = ttk.Frame(params)
        folder_frame.grid(row=7, column=1, sticky=tk.EW)
        folder_frame.columnconfigure(1, weight=1)
        self.var_output = tk.StringVar(value="")
        ttk.Button(
            folder_frame, text="Browse…", command=self._browse_output_folder
        ).grid(row=0, column=0, padx=(0, 6))
        ttk.Entry(folder_frame, textvariable=self.var_output, width=60).grid(
            row=0, column=1, sticky=tk.EW
        )

        # Bind folder changes to update preview (will be called from right column)
        self.var_output.trace("w", lambda *args: self._update_output_preview())

        # Visual separator below output folder section
        ttk.Separator(params, orient=tk.HORIZONTAL).grid(
            row=8, column=0, columnspan=2, sticky=tk.EW, pady=(8, 12))

        # ENH-07: Custom gap configuration with Fixed/Range modes + "?" helper
        gaps_label_frame = ttk.Frame(params)
        gaps_label_frame.grid(row=11, column=0, columnspan=2, sticky=tk.W, pady=(0, 4))
        ttk.Label(gaps_label_frame, text="Custom Gap Configuration (optional):").pack(side=tk.LEFT)
        gaps_help = tk.Label(gaps_label_frame, text="?", font=("Helvetica", 10, "bold"),
                            foreground="#0078d7", cursor="hand2")
        gaps_help.pack(side=tk.LEFT, padx=(4, 0))
        Tooltip(gaps_help, "Leave at 0 or disabled to use the Gap Type filter from Categories. Set a fixed value or range to override the gap type and use your custom values for all scenarios.")

        # Gap 1 controls — all on one row
        gap1_frame = ttk.Frame(params)
        gap1_frame.grid(row=12, column=0, columnspan=2, sticky=tk.EW, pady=(0, 4))
        for i in range(8):
            gap1_frame.columnconfigure(i, weight=0)

        ttk.Label(gap1_frame, text="Gap 1:").grid(row=0, column=0, sticky=tk.W, padx=(0, 8))

        self.var_gap1_mode = tk.StringVar(value="fixed")
        ttk.Radiobutton(gap1_frame, text="Fixed", variable=self.var_gap1_mode,
                       value="fixed", command=self._update_gap_ui).grid(
            row=0, column=1, sticky=tk.W, padx=(0, 4))

        # Fixed value spinbox (shown by default)
        self.var_gap1_value = tk.DoubleVar(value=5.0)
        self.gap1_spinbox = ttk.Spinbox(gap1_frame, from_=0, to=100, textvariable=self.var_gap1_value,
                   width=6, format="%.1f")
        self.gap1_spinbox.grid(row=0, column=2, sticky=tk.W, padx=(0, 16))

        ttk.Radiobutton(gap1_frame, text="Range", variable=self.var_gap1_mode,
                       value="range", command=self._update_gap_ui).grid(
            row=0, column=3, sticky=tk.W, padx=(0, 4))

        # Range min/max spinboxes (hidden by default)
        self.gap1_range_frame = ttk.Frame(gap1_frame)
        self.gap1_range_frame.grid(row=0, column=4, columnspan=4, sticky=tk.W)
        self.var_gap1_min = tk.DoubleVar(value=0.0)
        self.var_gap1_max = tk.DoubleVar(value=100.0)
        ttk.Label(self.gap1_range_frame, text="Min:").grid(row=0, column=0, sticky=tk.W, padx=(0, 2))
        ttk.Spinbox(self.gap1_range_frame, from_=0, to=100, textvariable=self.var_gap1_min,
                   width=6, format="%.1f").grid(row=0, column=1, sticky=tk.W, padx=(0, 8))
        ttk.Label(self.gap1_range_frame, text="Max:").grid(row=0, column=2, sticky=tk.W, padx=(0, 2))
        ttk.Spinbox(self.gap1_range_frame, from_=0, to=100, textvariable=self.var_gap1_max,
                   width=6, format="%.1f").grid(row=0, column=3, sticky=tk.W)

        # Gap 2 controls — all on one row
        gap2_frame = ttk.Frame(params)
        gap2_frame.grid(row=13, column=0, columnspan=2, sticky=tk.EW, pady=(0, 8))
        for i in range(8):
            gap2_frame.columnconfigure(i, weight=0)

        ttk.Label(gap2_frame, text="Gap 2:").grid(row=0, column=0, sticky=tk.W, padx=(0, 8))

        self.var_gap2_mode = tk.StringVar(value="fixed")
        ttk.Radiobutton(gap2_frame, text="Fixed", variable=self.var_gap2_mode,
                       value="fixed", command=self._update_gap_ui).grid(
            row=0, column=1, sticky=tk.W, padx=(0, 4))

        # Fixed value spinbox (shown by default)
        self.var_gap2_value = tk.DoubleVar(value=10.0)
        self.gap2_spinbox = ttk.Spinbox(gap2_frame, from_=0, to=100, textvariable=self.var_gap2_value,
                   width=6, format="%.1f")
        self.gap2_spinbox.grid(row=0, column=2, sticky=tk.W, padx=(0, 16))

        ttk.Radiobutton(gap2_frame, text="Range", variable=self.var_gap2_mode,
                       value="range", command=self._update_gap_ui).grid(
            row=0, column=3, sticky=tk.W, padx=(0, 4))

        # Range min/max spinboxes (hidden by default)
        self.gap2_range_frame = ttk.Frame(gap2_frame)
        self.gap2_range_frame.grid(row=0, column=4, columnspan=4, sticky=tk.W)
        self.var_gap2_min = tk.DoubleVar(value=0.0)
        self.var_gap2_max = tk.DoubleVar(value=100.0)
        ttk.Label(self.gap2_range_frame, text="Min:").grid(row=0, column=0, sticky=tk.W, padx=(0, 2))
        ttk.Spinbox(self.gap2_range_frame, from_=0, to=100, textvariable=self.var_gap2_min,
                   width=6, format="%.1f").grid(row=0, column=1, sticky=tk.W, padx=(0, 8))
        ttk.Label(self.gap2_range_frame, text="Max:").grid(row=0, column=2, sticky=tk.W, padx=(0, 2))
        ttk.Spinbox(self.gap2_range_frame, from_=0, to=100, textvariable=self.var_gap2_max,
                   width=6, format="%.1f").grid(row=0, column=3, sticky=tk.W)

        # Initial visibility (Fixed mode is default, so hide Range frames)
        self.gap1_range_frame.grid_remove()
        self.gap2_range_frame.grid_remove()

        # Visual separator below gap configuration section
        ttk.Separator(params, orient=tk.HORIZONTAL).grid(
            row=14, column=0, columnspan=2, sticky=tk.EW, pady=(8, 12))

        # Categories frame (checkboxes to filter scenario types)
        ttk.Label(params, text="Categories (leave unchecked for all):").grid(
            row=15, column=0, columnspan=2, sticky=tk.W, pady=(0, 4)
        )

        cat_frame = ttk.Frame(params)
        cat_frame.grid(row=16, column=0, columnspan=2, sticky=tk.EW, pady=(0, 8))
        cat_frame.columnconfigure(0, weight=1)
        cat_frame.columnconfigure(1, weight=1)
        cat_frame.columnconfigure(2, weight=1)
        cat_frame.columnconfigure(3, weight=1)

        # Velocity types column
        ttk.Label(cat_frame, text="Velocity", font=("Helvetica", 9, "bold")).grid(
            row=0, column=0, sticky=tk.W, padx=(0, 10)
        )
        self.var_vel_nV = tk.BooleanVar(value=False)
        self.var_vel_mV = tk.BooleanVar(value=False)
        self.var_vel_hV = tk.BooleanVar(value=False)
        self.var_vel_hB = tk.BooleanVar(value=False)
        ttk.Checkbutton(cat_frame, text="Nominal (nV)", variable=self.var_vel_nV).grid(
            row=1, column=0, sticky=tk.W
        )
        ttk.Checkbutton(cat_frame, text="Medium Variable (mV)", variable=self.var_vel_mV).grid(
            row=2, column=0, sticky=tk.W
        )
        ttk.Checkbutton(cat_frame, text="High Variable (hV)", variable=self.var_vel_hV).grid(
            row=3, column=0, sticky=tk.W
        )
        ttk.Checkbutton(cat_frame, text="Hard Brake (hB)", variable=self.var_vel_hB).grid(
            row=4, column=0, sticky=tk.W
        )

        # Gap types column
        ttk.Label(cat_frame, text="Gap Type", font=("Helvetica", 9, "bold")).grid(
            row=0, column=1, sticky=tk.W, padx=(0, 10)
        )
        self.var_gap_sG = tk.BooleanVar(value=False)
        self.var_gap_mG = tk.BooleanVar(value=False)
        self.var_gap_bG = tk.BooleanVar(value=False)
        self.var_gap_vG = tk.BooleanVar(value=False)
        ttk.Checkbutton(cat_frame, text="Small (sG)", variable=self.var_gap_sG).grid(
            row=1, column=1, sticky=tk.W
        )
        ttk.Checkbutton(cat_frame, text="Medium (mG)", variable=self.var_gap_mG).grid(
            row=2, column=1, sticky=tk.W
        )
        ttk.Checkbutton(cat_frame, text="Big (bG)", variable=self.var_gap_bG).grid(
            row=3, column=1, sticky=tk.W
        )
        ttk.Checkbutton(cat_frame, text="Variant (vG)", variable=self.var_gap_vG).grid(
            row=4, column=1, sticky=tk.W
        )

        # Loss types column
        ttk.Label(cat_frame, text="Loss Type", font=("Helvetica", 9, "bold")).grid(
            row=0, column=2, sticky=tk.W, padx=(0, 10)
        )
        self.var_loss_qs = tk.BooleanVar(value=False)
        self.var_loss_sl = tk.BooleanVar(value=False)
        self.var_loss_fv = tk.BooleanVar(value=False)
        ttk.Checkbutton(cat_frame, text="Quick-Short (qs)", variable=self.var_loss_qs).grid(
            row=1, column=2, sticky=tk.W
        )
        ttk.Checkbutton(cat_frame, text="Slow (sl)", variable=self.var_loss_sl).grid(
            row=2, column=2, sticky=tk.W
        )
        ttk.Checkbutton(cat_frame, text="Frequent Variant (fv)", variable=self.var_loss_fv).grid(
            row=3, column=2, sticky=tk.W
        )

        # FORT column
        ttk.Label(cat_frame, text="FORT Events", font=("Helvetica", 9, "bold")).grid(
            row=0, column=3, sticky=tk.W
        )
        self.var_fort_yes = tk.BooleanVar(value=False)
        self.var_fort_no = tk.BooleanVar(value=False)
        ttk.Checkbutton(cat_frame, text="Include FORT", variable=self.var_fort_yes).grid(
            row=1, column=3, sticky=tk.W
        )
        ttk.Checkbutton(cat_frame, text="Exclude FORT", variable=self.var_fort_no).grid(
            row=2, column=3, sticky=tk.W
        )

        # Generate, Pause, and Stop buttons
        btn_frame = ttk.Frame(params)
        btn_frame.grid(row=20, column=0, columnspan=2, pady=(12, 4))

        self.gen_btn = ttk.Button(
            btn_frame,
            text="Generate Scenarios",
            style="Accent.TButton",
            command=self._start_generation,
        )
        self.gen_btn.pack(side=tk.LEFT, padx=(0, 4))

        self.pause_btn = ttk.Button(
            btn_frame,
            text="Pause",
            command=self._toggle_pause,
            state=tk.DISABLED,
        )
        self.pause_btn.pack(side=tk.LEFT, padx=(0, 4))

        self.stop_btn = ttk.Button(
            btn_frame,
            text="Stop",
            command=self._stop_generation,
            state=tk.DISABLED,
        )
        self.stop_btn.pack(side=tk.LEFT)

        # ── Output folder preview panel (RIGHT column) ─────────────────
        preview_container = ttk.LabelFrame(params_container, text="Output Folder Contents", padding=8)
        preview_container.grid(row=0, column=1, sticky=tk.NSEW, padx=0, pady=0)
        preview_container.columnconfigure(0, weight=1)
        preview_container.rowconfigure(0, weight=1)

        self.output_preview_listbox = tk.Listbox(
            preview_container, height=25, relief=tk.SUNKEN, selectmode=tk.SINGLE, width=35
        )
        self.output_preview_listbox.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)

        scroll = ttk.Scrollbar(
            preview_container, orient=tk.VERTICAL, command=self.output_preview_listbox.yview
        )
        scroll.grid(row=0, column=1, sticky="ns", padx=(0, 0), pady=0)
        self.output_preview_listbox.config(yscrollcommand=scroll.set)

        # ── Progress frame ───────────────────────────────────────────
        prog = ttk.LabelFrame(tab, text="Progress", padding=10)
        prog.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        self.progress_var = tk.DoubleVar(value=0.0)
        ttk.Progressbar(
            prog, variable=self.progress_var, maximum=100, mode="determinate"
        ).pack(fill=tk.X, pady=(0, 4))

        self.progress_label_var = tk.StringVar(value="Ready to generate.")
        ttk.Label(prog, textvariable=self.progress_label_var).pack(
            anchor=tk.W, pady=(0, 4)
        )

        # Log text — 1/3 height (~6 lines)
        log_frame = ttk.Frame(prog)
        log_frame.pack(fill=tk.BOTH, expand=True)

        self.log_text = tk.Text(
            log_frame, height=6, state=tk.DISABLED, wrap=tk.WORD
        )
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Colour tags for log levels
        self.log_text.tag_configure("error",   foreground="#cc0000")
        self.log_text.tag_configure("success", foreground="#007700")
        self.log_text.tag_configure("warning", foreground="#bb6600")

        log_scroll = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.config(yscrollcommand=log_scroll.set)

    def _load_settings(self) -> None:
        """Load settings from INI file if it exists."""
        if not os.path.exists(self.settings_file):
            return

        try:
            config = configparser.ConfigParser()
            config.read(self.settings_file)

            if "parameters" in config:
                sect = config["parameters"]
                if "duration" in sect:
                    self.var_duration.set(sect["duration"])
                if "max_events" in sect:
                    self.var_max_events.set(sect["max_events"])
                if "min_sep" in sect:
                    self.var_min_sep.set(sect["min_sep"])
                if "count" in sect:
                    self.var_count.set(sect["count"])
                if "seed" in sect:
                    self.var_seed.set(sect["seed"])
                if "output" in sect:
                    self.var_output.set(sect["output"])
                if "params_file" in sect:
                    self.var_params_file.set(sect["params_file"])
                if "max_velocity" in sect:
                    self.var_max_velocity.set(sect["max_velocity"])
                if "max_acceleration" in sect:
                    self.var_max_acceleration.set(sect["max_acceleration"])

            if "gaps" in config:
                sect = config["gaps"]
                if "gap1_mode" in sect:
                    self.var_gap1_mode.set(sect["gap1_mode"])
                if "gap1_value" in sect:
                    self.var_gap1_value.set(sect["gap1_value"])
                if "gap1_min" in sect:
                    self.var_gap1_min.set(sect["gap1_min"])
                if "gap1_max" in sect:
                    self.var_gap1_max.set(sect["gap1_max"])
                if "gap2_mode" in sect:
                    self.var_gap2_mode.set(sect["gap2_mode"])
                if "gap2_value" in sect:
                    self.var_gap2_value.set(sect["gap2_value"])
                if "gap2_min" in sect:
                    self.var_gap2_min.set(sect["gap2_min"])
                if "gap2_max" in sect:
                    self.var_gap2_max.set(sect["gap2_max"])
                # Update UI to show correct fields
                self._update_gap_ui()
        except Exception as e:
            print(f"Warning: Could not load settings: {e}")

    def _save_settings(self) -> None:
        """Save settings to INI file."""
        try:
            config = configparser.ConfigParser()

            config["parameters"] = {
                "duration": str(self.var_duration.get()),
                "max_events": str(self.var_max_events.get()),
                "min_sep": str(self.var_min_sep.get()),
                "count": str(self.var_count.get()),
                "seed": str(self.var_seed.get()),
                "output": str(self.var_output.get()),
                "params_file": str(self.var_params_file.get()),
                "max_velocity": str(self.var_max_velocity.get()),
                "max_acceleration": str(self.var_max_acceleration.get()),
            }

            config["gaps"] = {
                "gap1_mode": str(self.var_gap1_mode.get()),
                "gap1_value": str(self.var_gap1_value.get()),
                "gap1_min": str(self.var_gap1_min.get()),
                "gap1_max": str(self.var_gap1_max.get()),
                "gap2_mode": str(self.var_gap2_mode.get()),
                "gap2_value": str(self.var_gap2_value.get()),
                "gap2_min": str(self.var_gap2_min.get()),
                "gap2_max": str(self.var_gap2_max.get()),
            }

            with open(self.settings_file, "w") as f:
                config.write(f)
        except Exception as e:
            print(f"Warning: Could not save settings: {e}")

    def _on_closing(self) -> None:
        """Called when the user closes the window."""
        self._save_settings()
        self.root.destroy()

    def _param_row(
        self, parent, row: int, label: str, attr: str, var_cls, default
    ) -> None:
        """Add a labelled entry row to a grid frame and set self.<attr>."""
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky=tk.W, pady=4)
        var = var_cls(value=default)
        setattr(self, attr, var)
        ttk.Entry(parent, textvariable=var, width=14).grid(
            row=row, column=1, sticky=tk.W
        )

    def _browse_parameters_file(self) -> None:
        """Open file dialog to select a parameters CSV file and load its values."""
        path = filedialog.askopenfilename(
            title="Select Parameters File",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if path:
            self.var_params_file.set(path)
            self._load_parameters_file(path)

    def _load_parameters_file(self, path: str) -> None:
        """
        Parse a ConvoySIM parameters CSV file and populate the Max Velocity
        and Max Acceleration spinboxes.

        Expected format (e.g. parameters_3.csv):
            Parameter,Value,Unit,Description
            Max velocity,17,kph,Maximum allowed truck velocity
            Max acceleration,1.2,m/s^2,Maximum positive acceleration

        The parser is case-insensitive and ignores extra columns / blank lines.
        """
        try:
            with open(path, "r") as fh:
                lines = fh.readlines()

            loaded = {}
            for line in lines:
                parts = line.strip().split(",")
                if len(parts) < 2:
                    continue
                param_name = parts[0].strip().lower()
                raw_value  = parts[1].strip()
                try:
                    value = float(raw_value)
                except ValueError:
                    continue

                if "max velocity" in param_name or "max_velocity" in param_name:
                    self.var_max_velocity.set(value)
                    loaded["max_velocity"] = value
                elif "max acceleration" in param_name or "max_acceleration" in param_name:
                    self.var_max_acceleration.set(value)
                    loaded["max_acceleration"] = value

            if loaded:
                parts_str = ", ".join(f"{k}={v}" for k, v in loaded.items())
                self._log(
                    f"Parameters loaded from {os.path.basename(path)}: {parts_str}",
                    "success",
                )
            else:
                self._log(
                    f"No recognised parameters found in {os.path.basename(path)}. "
                    "Expected rows: 'Max velocity' and/or 'Max acceleration'.",
                    "warning",
                )
        except Exception as exc:
            self._log(f"Could not load parameters file: {exc}", "error")

    def _update_gap_ui(self) -> None:
        """Toggle visibility of Gap spinbox vs range fields based on selected mode."""
        # Gap 1: Fixed value spinbox or Range min/max
        if self.var_gap1_mode.get() == "fixed":
            self.gap1_spinbox.grid()
            self.gap1_range_frame.grid_remove()
        else:  # range
            self.gap1_spinbox.grid_remove()
            self.gap1_range_frame.grid()

        # Gap 2: Fixed value spinbox or Range min/max
        if self.var_gap2_mode.get() == "fixed":
            self.gap2_spinbox.grid()
            self.gap2_range_frame.grid_remove()
        else:  # range
            self.gap2_spinbox.grid_remove()
            self.gap2_range_frame.grid()

    # ═════════════════════════════════════════════════════════════════════════
    # Tab 2 — Scenarios (merged Browser + Viewer)
    # ═════════════════════════════════════════════════════════════════════════

    def _build_scenarios_tab(self) -> None:
        tab = self.tab_scenarios

        # Outer vertical paned: top strip (list + details) vs bottom (table)
        outer = ttk.PanedWindow(tab, orient=tk.VERTICAL)
        outer.pack(fill=tk.BOTH, expand=True, padx=6, pady=6)

        # ── Top: horizontal split of list (left) and details (right) ──
        top_paned = ttk.PanedWindow(outer, orient=tk.HORIZONTAL)
        outer.add(top_paned, weight=1)

        # Left — scenario list
        list_frame = ttk.LabelFrame(top_paned, text="Scenarios", padding=4)
        top_paned.add(list_frame, weight=1)

        list_scroll = ttk.Scrollbar(list_frame)
        list_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.scenario_listbox = tk.Listbox(
            list_frame,
            yscrollcommand=list_scroll.set,
            activestyle="dotbox",
            selectmode=tk.SINGLE,
            font=("Courier", 10),
        )
        self.scenario_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scenario_listbox.bind("<<ListboxSelect>>", self._on_scenario_selected)
        list_scroll.config(command=self.scenario_listbox.yview)

        # Right — scenario details
        details_frame = ttk.LabelFrame(top_paned, text="Details", padding=8)
        top_paned.add(details_frame, weight=2)

        self.details_text = tk.Text(
            details_frame,
            state=tk.DISABLED,
            wrap=tk.WORD,
            height=10,
            font=("Courier", 10),
        )
        self.details_text.pack(fill=tk.BOTH, expand=True)

        # ── Bottom: editable data table ───────────────────────────────
        table_frame = ttk.LabelFrame(
            outer,
            text="Scenario Data  (double-click a cell to edit)",
            padding=4,
        )
        outer.add(table_frame, weight=3)

        # Treeview + scrollbars
        tv_frame = ttk.Frame(table_frame)
        tv_frame.pack(fill=tk.BOTH, expand=True)
        tv_frame.rowconfigure(0, weight=1)
        tv_frame.columnconfigure(0, weight=1)

        self.data_tree = ttk.Treeview(
            tv_frame,
            columns=self.CSV_COLUMNS,
            show="headings",
            selectmode="browse",
        )
        for col, heading, width in zip(
            self.CSV_COLUMNS, self.CSV_HEADINGS, self.CSV_COL_WIDTHS
        ):
            self.data_tree.heading(col, text=heading)
            self.data_tree.column(
                col,
                width=width,
                minwidth=50,
                stretch=(col == "Notes"),
            )

        tv_vs = ttk.Scrollbar(tv_frame, orient=tk.VERTICAL,   command=self.data_tree.yview)
        tv_hs = ttk.Scrollbar(tv_frame, orient=tk.HORIZONTAL, command=self.data_tree.xview)
        self.data_tree.configure(yscrollcommand=tv_vs.set, xscrollcommand=tv_hs.set)

        self.data_tree.grid(row=0, column=0, sticky="nsew")
        tv_vs.grid(row=0, column=1, sticky="ns")
        tv_hs.grid(row=1, column=0, sticky="ew")

        # Bindings
        self.data_tree.bind("<Double-1>",  self._on_cell_double_click)
        self.data_tree.bind("<Button-1>",  self._dismiss_cell_editor)

        # Buttons below the table
        btn_bar = ttk.Frame(table_frame)
        btn_bar.pack(fill=tk.X, pady=(4, 0))

        ttk.Button(btn_bar, text="+ Add Row Below", command=self._add_table_row).pack(
            side=tk.LEFT, padx=(0, 4)
        )
        ttk.Button(btn_bar, text="− Remove Row", command=self._remove_table_row).pack(
            side=tk.LEFT
        )
        ttk.Button(btn_bar, text="Save As…", command=self._save_table_as).pack(
            side=tk.RIGHT
        )
        ttk.Button(btn_bar, text="Save",    command=self._save_table).pack(
            side=tk.RIGHT, padx=(0, 4)
        )

    # ═════════════════════════════════════════════════════════════════════════
    # Generation logic
    # ═════════════════════════════════════════════════════════════════════════

    def _start_generation(self) -> None:
        if self.generation_running:
            self._log("Generation already in progress.", "warning")
            return

        # Validate inputs
        try:
            duration         = float(self.var_duration.get())
            max_events       = int(self.var_max_events.get())
            min_sep          = float(self.var_min_sep.get())
            count            = int(self.var_count.get())
            max_velocity_kph = float(self.var_max_velocity.get())
            max_accel_mps2   = float(self.var_max_acceleration.get())
        except (ValueError, tk.TclError):
            self._log("Invalid parameter values — all fields must be numeric.", "error")
            return

        seed_str = self.var_seed.get().strip()
        try:
            seed = int(seed_str) if seed_str else None
        except ValueError:
            self._log("Random Seed must be an integer (e.g. 42) or left blank.", "error")
            return

        # Always write into a timestamped subfolder so each run is isolated.
        # The field holds the "Scene_Gen root"; if blank, "Scene_Gen" is used.
        scene_gen_root = self.var_output.get().strip() or "Scene_Gen"
        timestamp = datetime.now().strftime("%d%m%Y_%H%M")
        output_folder = os.path.join(scene_gen_root, timestamp)

        # Collect selected categories from checkboxes
        selected_categories = []

        # Velocity types
        if self.var_vel_nV.get():
            selected_categories.append("velocity_type:nV")
        if self.var_vel_mV.get():
            selected_categories.append("velocity_type:mV")
        if self.var_vel_hV.get():
            selected_categories.append("velocity_type:hV")
        if self.var_vel_hB.get():
            selected_categories.append("velocity_type:hB")

        # Gap types
        if self.var_gap_sG.get():
            selected_categories.append("gap_type:sG")
        if self.var_gap_mG.get():
            selected_categories.append("gap_type:mG")
        if self.var_gap_bG.get():
            selected_categories.append("gap_type:bG")
        if self.var_gap_vG.get():
            selected_categories.append("gap_type:vG")

        # Loss types
        if self.var_loss_qs.get():
            selected_categories.append("loss_type:qs")
        if self.var_loss_sl.get():
            selected_categories.append("loss_type:sl")
        if self.var_loss_fv.get():
            selected_categories.append("loss_type:fv")

        # FORT
        if self.var_fort_yes.get():
            selected_categories.append("fort:yes")
        if self.var_fort_no.get():
            selected_categories.append("fort:no")

        # ENH-07: Collect gap configuration from UI
        gap_configurations = []

        # Gap 1
        if self.var_gap1_mode.get() == "fixed":
            gap1_config = GapConfiguration(
                gap_index=0,
                is_fixed=True,
                fixed_value=self.var_gap1_value.get(),
                min_value=0,
                max_value=0
            )
        else:  # range
            gap1_config = GapConfiguration(
                gap_index=0,
                is_fixed=False,
                fixed_value=0,
                min_value=self.var_gap1_min.get(),
                max_value=self.var_gap1_max.get()
            )

        # Gap 2
        if self.var_gap2_mode.get() == "fixed":
            gap2_config = GapConfiguration(
                gap_index=1,
                is_fixed=True,
                fixed_value=self.var_gap2_value.get(),
                min_value=0,
                max_value=0
            )
        else:  # range
            gap2_config = GapConfiguration(
                gap_index=1,
                is_fixed=False,
                fixed_value=0,
                min_value=self.var_gap2_min.get(),
                max_value=self.var_gap2_max.get()
            )

        gap_configurations = [gap1_config, gap2_config]

        try:
            config = ScenarioConfig(
                scenario_duration_s=duration,
                max_events=max_events,
                min_event_separation_s=min_sep,
                num_scenarios=count,
                selected_categories=selected_categories,
                gap_configurations=gap_configurations,
                max_velocity_kph=max_velocity_kph,
                max_acceleration_mps2=max_accel_mps2,
            )
            config.validate()
        except ValueError as exc:
            self._log(f"Invalid configuration: {exc}", "error")
            return

        # Clear log and reset progress bar
        self._clear_log()
        self.progress_var.set(0.0)
        self.progress_label_var.set("Starting…")

        seed_label = str(seed) if seed is not None else "random"
        self._log(f"Starting generation: {count} scenarios  seed={seed_label}")

        # Clear stop/pause signals and enable control buttons
        self.stop_signal.clear()
        self.pause_event.clear()
        self.generation_running = True
        self.gen_btn.config(state=tk.DISABLED)
        self.pause_btn.config(state=tk.NORMAL, text="Pause")
        self.stop_btn.config(state=tk.NORMAL)

        thread = threading.Thread(
            target=self._generation_thread,
            args=(config, seed, output_folder),
            daemon=True,
        )
        thread.start()

    def _stop_generation(self) -> None:
        """Signal the generation thread to stop."""
        self._log("Stopping generation…", "warning")
        self.stop_signal.set()
        self.stop_btn.config(state=tk.DISABLED)

    def _toggle_pause(self) -> None:
        """Toggle pause/resume for generation."""
        if self.pause_event.is_set():
            # Currently paused — resume
            self.pause_event.clear()
            self._log("Resuming generation…", "success")
            self.pause_btn.config(text="Pause")
        else:
            # Currently running — pause
            self.pause_event.set()
            self._log("Pausing generation…", "warning")
            self.pause_btn.config(text="Resume")

    def _generation_thread(
        self, config: ScenarioConfig, seed: Optional[int], output_folder: str
    ) -> None:
        try:
            def on_progress(current: int, total: int) -> None:
                import time
                # Check for stop signal
                if self.stop_signal.is_set():
                    raise RuntimeError("Generation stopped by user")

                # Check for pause and sleep while paused
                while self.pause_event.is_set():
                    if self.stop_signal.is_set():
                        raise RuntimeError("Generation stopped by user")
                    time.sleep(0.1)  # Sleep briefly before checking again

                pct = (current / total) * 100
                self.progress_var.set(pct)
                self.progress_label_var.set(
                    f"Generated {current} / {total} scenarios…"
                )

            gen = ScenarioGenerator(
                config, seed=seed, progress_callback=on_progress
            )
            self.scenarios = gen.generate_all()

            # Check if stop was requested after generation finished
            if self.stop_signal.is_set():
                raise RuntimeError("Generation stopped by user")

            self.progress_label_var.set(
                f"Done — exporting {len(self.scenarios)} files…"
            )
            self._log(
                f"Generation complete — {len(self.scenarios)} scenarios.", "success"
            )

            os.makedirs(output_folder, exist_ok=True)
            paths = CSVWriter.write_scenarios_batch(self.scenarios, output_folder)
            self.scenario_paths = paths

            self._log(
                f"Exported {len(paths)} CSV files → {output_folder}", "success"
            )
            # ENH-11: Refresh output folder preview after generation
            self._update_output_preview()
            self.progress_var.set(100.0)
            self.progress_label_var.set(
                f"Complete — {len(self.scenarios)} scenarios in {output_folder}"
            )
            self._update_status(
                f"Generated {len(self.scenarios)} scenarios → {output_folder}"
            )

            # Populate Scenarios tab on the UI thread
            self.root.after(0, self._populate_scenario_list)

        except RuntimeError as exc:
            if "stopped by user" in str(exc).lower():
                self._log("Generation stopped.", "warning")
                self.progress_label_var.set("Generation stopped by user.")
                self._update_status("Generation stopped.")
            else:
                self._log(f"Generation failed: {exc}", "error")
                self.progress_label_var.set("Generation failed — see log above.")
                self._update_status("Generation failed.")
        except Exception as exc:
            self._log(f"Generation failed: {exc}", "error")
            self.progress_label_var.set("Generation failed — see log above.")
            self._update_status("Generation failed.")
        finally:
            self.generation_running = False
            self.gen_btn.config(state=tk.NORMAL)
            self.pause_btn.config(state=tk.DISABLED, text="Pause")
            self.stop_btn.config(state=tk.DISABLED)
            # Clear pause state on finish
            self.pause_event.clear()

    # ═════════════════════════════════════════════════════════════════════════
    # Scenario browser
    # ═════════════════════════════════════════════════════════════════════════

    def _populate_scenario_list(self) -> None:
        """Rebuild the listbox after generation and switch to Scenarios tab."""
        self.scenario_listbox.delete(0, tk.END)
        for i, sc in enumerate(self.scenarios):
            self.scenario_listbox.insert(tk.END, f"{i + 1:>3}.  {sc.metadata.name}")

        if self.scenarios:
            self.scenario_listbox.select_set(0)
            self._show_scenario(0)
            self.notebook.select(self.tab_scenarios)

    def _on_scenario_selected(self, event=None) -> None:
        sel = self.scenario_listbox.curselection()
        if sel:
            self._show_scenario(sel[0])

    def _show_scenario(self, index: int) -> None:
        """Display details and data table for the scenario at *index*."""
        if not (0 <= index < len(self.scenarios)):
            return
        self.current_scenario_index = index
        scenario = self.scenarios[index]

        # ── Details panel ─────────────────────────────────────────
        gap_str  = ",  ".join(f"{g:g} m" for g in scenario.initial_gaps)
        fort_str = (
            f"Yes — at {scenario.fort_event.timestamp_s:.1f} s"
            if scenario.fort_event
            else "No"
        )
        total_events = len(scenario.get_all_events())
        seed_str = str(scenario.metadata.seed) if scenario.metadata.seed else "—"

        detail_lines = [
            f"Name:         {scenario.metadata.name}",
            f"Description:  {scenario.metadata.description}",
            "",
            f"Trucks:       {scenario.truck_count}",
            f"Duration:     {scenario.scenario_duration_s:.0f} s",
            f"Velocity:     {scenario.velocity_type.name}",
            f"Gap type:     {scenario.gap_type.name}",
            f"Init. gaps:   {gap_str}",
            f"Loss pairs:   {len(scenario.loss_resume_pairs)}",
            f"FORT:         {fort_str}",
            f"Total events: {total_events}",
            "",
            f"Seed used:    {seed_str}",
        ]

        self.details_text.config(state=tk.NORMAL)
        self.details_text.delete(1.0, tk.END)
        self.details_text.insert(tk.END, "\n".join(detail_lines))
        self.details_text.config(state=tk.DISABLED)

        # ── Data table ────────────────────────────────────────────
        self._dismiss_cell_editor()
        self.data_tree.delete(*self.data_tree.get_children())

        for idx, row in enumerate(CSVWriter.scenario_to_csv_rows(scenario)):
            # ENH-08: Zebra striping — alternate background colors for even/odd rows
            tag = "TreenodeOdd.Treeview" if idx % 2 == 0 else "TreenodeEven.Treeview"
            self.data_tree.insert(
                "", tk.END,
                tags=(tag,),
                values=(
                    f"{row.time_s:.0f}",
                    f"{row.truck1_velocity_kph:.2f}" if row.truck1_velocity_kph is not None else "",
                    row.truck1_event        or "",
                    row.truck2_image_event  or "",
                    row.truck3_image_event  or "",
                    row.notes               or "",
                ),
            )

    # ═════════════════════════════════════════════════════════════════════════
    # Editable table
    # ═════════════════════════════════════════════════════════════════════════

    def _on_cell_double_click(self, event: tk.Event) -> None:
        """Open an in-cell Entry or Combobox widget on double-click (ENH-10)."""
        # Dismiss any existing editor first (commits its value)
        self._dismiss_cell_editor()

        if self.data_tree.identify_region(event.x, event.y) != "cell":
            return

        col_id  = self.data_tree.identify_column(event.x)   # "#1", "#2", …
        row_id  = self.data_tree.identify_row(event.y)
        if not row_id:
            return

        bbox = self.data_tree.bbox(row_id, col_id)
        if not bbox:
            return
        x, y, w, h = bbox

        col_index = int(col_id.lstrip("#")) - 1
        col_name  = self.CSV_COLUMNS[col_index]
        current   = self.data_tree.set(row_id, col_name)

        # ENH-10: Use Combobox for Truck1_Event column (only valid values)
        if col_name == "Truck1_Event":
            editor = ttk.Combobox(
                self.data_tree,
                values=["", "FORT activated"],
                state="readonly",
                width=w // 7,  # Approximate width
            )
            editor.place(x=x, y=y, width=w, height=h)
            editor.set(current)
            editor.focus_set()
        else:
            # Standard Entry for other columns
            editor = tk.Entry(self.data_tree, borderwidth=1, relief=tk.SOLID)
            editor.place(x=x, y=y, width=w, height=h)
            editor.insert(0, current)
            editor.select_range(0, tk.END)
            editor.focus_set()

        # Store references so _dismiss_cell_editor can commit the value
        self._cell_editor  = editor
        self._edit_row_id  = row_id
        self._edit_col_name = col_name

        def _commit(e=None):
            # Only act if this editor is still the active editor
            if self._cell_editor is editor:
                self.data_tree.set(self._edit_row_id, self._edit_col_name, editor.get())
                self._cell_editor  = None
                self._edit_row_id  = None
                self._edit_col_name = None
                editor.destroy()

        def _discard(e=None):
            if self._cell_editor is editor:
                self._cell_editor  = None
                self._edit_row_id  = None
                self._edit_col_name = None
                editor.destroy()

        editor.bind("<Return>",   _commit)
        editor.bind("<Tab>",      _commit)
        editor.bind("<Escape>",   _discard)
        editor.bind("<FocusOut>", _commit)

    def _dismiss_cell_editor(self, event=None) -> None:
        """Commit and destroy any open cell editor (called on single-click / scroll)."""
        if self._cell_editor is not None:
            try:
                if self._cell_editor.winfo_exists():
                    self.data_tree.set(
                        self._edit_row_id,
                        self._edit_col_name,
                        self._cell_editor.get(),
                    )
                    self._cell_editor.destroy()
            except tk.TclError:
                pass
            self._cell_editor   = None
            self._edit_row_id   = None
            self._edit_col_name = None

    def _add_table_row(self) -> None:
        """Insert a blank row after the selected row (or at the end)."""
        blank = ("", "", "", "", "", "")
        sel = self.data_tree.selection()
        if sel:
            idx = self.data_tree.index(sel[0])
            new_id = self.data_tree.insert("", idx + 1, values=blank)
        else:
            new_id = self.data_tree.insert("", tk.END, values=blank)
        self.data_tree.selection_set(new_id)

    def _remove_table_row(self) -> None:
        """Delete the currently selected row."""
        sel = self.data_tree.selection()
        if sel:
            self.data_tree.delete(sel[0])
        else:
            self._log("Select a row first, then click − Remove Row.", "warning")

    def _build_csv_from_table(self) -> str:
        """Reconstruct the full CSV text from scenario metadata + table rows."""
        if self.current_scenario_index < 0 or not self.scenarios:
            return ""
        scenario = self.scenarios[self.current_scenario_index]

        lines = [
            CSVWriter.format_description_row(scenario),
            CSVWriter.format_initial_gaps_row(scenario),
            CSVWriter.format_header_row(),
        ]
        for row_id in self.data_tree.get_children():
            cells = [self.data_tree.set(row_id, col) for col in self.CSV_COLUMNS]
            lines.append(",".join(cells))

        return "\n".join(lines)

    def _save_table(self) -> None:
        """Overwrite the scenario's original exported CSV file."""
        if self.current_scenario_index < 0:
            self._log("No scenario selected.", "warning")
            return
        if self.current_scenario_index < len(self.scenario_paths):
            self._write_csv_to(self.scenario_paths[self.current_scenario_index])
        else:
            self._save_table_as()

    def _save_table_as(self) -> None:
        """Save the current table to a user-chosen path and refresh scenario list (ENH-12)."""
        if self.current_scenario_index < 0:
            self._log("No scenario selected.", "warning")
            return
        scenario = self.scenarios[self.current_scenario_index]
        path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=f"{scenario.metadata.name}.csv",
            title="Save Scenario As",
        )
        if path:
            self._write_csv_to(path)
            # ENH-12: Refresh scenario list from the folder where file was saved
            save_folder = os.path.dirname(path)
            self._load_scenarios_from_folder(save_folder)

    def _write_csv_to(self, path: str) -> None:
        csv_text = self._build_csv_from_table()
        try:
            with open(path, "w", newline="") as fh:
                fh.write(csv_text)
            self._log(f"Saved: {path}", "success")
            self._update_status(f"Saved {os.path.basename(path)}")
        except OSError as exc:
            self._log(f"Save failed: {exc}", "error")

    # ═════════════════════════════════════════════════════════════════════════
    # File operations
    # ═════════════════════════════════════════════════════════════════════════

    def _browse_output_folder(self) -> None:
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self.var_output.set(folder)
            self._update_output_preview()

    def _update_output_preview(self) -> None:
        """
        Update the output folder preview listbox with CSV files (ENH-11).
        Called whenever the output folder path changes.
        """
        self.output_preview_listbox.delete(0, tk.END)
        folder = self.var_output.get()

        if not folder or not os.path.isdir(folder):
            self.output_preview_listbox.insert(tk.END, "(folder not found)")
            return

        try:
            csv_files = sorted([f for f in os.listdir(folder) if f.endswith(".csv")])
            if not csv_files:
                self.output_preview_listbox.insert(tk.END, "(no CSV files)")
            else:
                for csv_file in csv_files:
                    self.output_preview_listbox.insert(tk.END, csv_file)
        except OSError:
            self.output_preview_listbox.insert(tk.END, "(cannot read folder)")

    def _open_scenarios_folder(self) -> None:
        """Load scenario file list from an existing folder (filenames only)."""
        folder = filedialog.askdirectory(title="Open Scenarios Folder")
        if not folder:
            return
        self._load_scenarios_from_folder(folder)

    def _load_scenarios_from_folder(self, folder: str) -> None:
        """
        Load scenario CSV files from a folder and update the listbox (ENH-12).

        Args:
            folder: Folder containing CSV files
        """
        csv_files = sorted(f for f in os.listdir(folder) if f.endswith(".csv"))
        if not csv_files:
            self._log(f"No CSV files found in: {folder}", "warning")
            return

        self.scenario_listbox.delete(0, tk.END)
        self.scenarios      = []
        self.scenario_paths = []
        for i, name in enumerate(csv_files):
            self.scenario_listbox.insert(tk.END, f"{i + 1:>3}.  {name[:-4]}")
            self.scenario_paths.append(os.path.join(folder, name))

        self._log(
            f"Opened {len(csv_files)} scenario files from: {folder}", "success"
        )
        self.notebook.select(self.tab_scenarios)

    # ═════════════════════════════════════════════════════════════════════════
    # Logging & status
    # ═════════════════════════════════════════════════════════════════════════

    def _log(self, message: str, level: str = "info") -> None:
        """
        Append a timestamped, colour-coded log line.

        Levels
        ------
        "info"    — default colour
        "success" — green
        "warning" — orange
        "error"   — red
        """
        prefix_map = {
            "info":    "    ",
            "success": " OK ",
            "warning": "WARN",
            "error":   "ERR ",
        }
        prefix = prefix_map.get(level, "    ")
        ts   = datetime.now().strftime("%H:%M:%S")
        line = f"{ts} [{prefix}] {message}\n"

        self.log_text.config(state=tk.NORMAL)
        tag = level if level != "info" else ""
        self.log_text.insert(tk.END, line, tag)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def _clear_log(self) -> None:
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)

    def _update_status(self, message: str) -> None:
        self.statusbar.config(text=message)

    # ═════════════════════════════════════════════════════════════════════════
    # Help & About
    # ═════════════════════════════════════════════════════════════════════════

    def _show_help(self) -> None:
        """Open the Help window."""
        win = tk.Toplevel(self.root)
        win.title("SimGenerator Help")
        win.geometry("620x560")
        win.resizable(True, True)
        win.transient(self.root)
        win.grab_set()

        frame = ttk.Frame(win)
        frame.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        scroll = ttk.Scrollbar(frame)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        text = tk.Text(
            frame, wrap=tk.WORD, padx=14, pady=10,
            relief=tk.FLAT, yscrollcommand=scroll.set
        )
        text.pack(fill=tk.BOTH, expand=True)
        scroll.config(command=text.yview)

        text.insert(tk.END, _HELP_TEXT)
        text.config(state=tk.DISABLED)

        ttk.Button(win, text="Close", command=win.destroy).pack(pady=6)

    def _show_about(self) -> None:
        win = tk.Toplevel(self.root)
        win.title("About SimGenerator")
        win.geometry("320x180")
        win.resizable(False, False)
        win.transient(self.root)
        win.grab_set()

        ttk.Label(win, text="SimGenerator v1.0", style="Title.TLabel").pack(pady=(20, 4))
        ttk.Label(win, text="Convoy Scenario Generator for ConvoySIM").pack()
        ttk.Label(win, text="Pure Python · Tkinter · No external dependencies").pack()
        ttk.Button(win, text="Close", command=win.destroy).pack(pady=18)


# ─────────────────────────────────────────────────────────────────────────────
# Help text (shown in the ? Help popup)
# ─────────────────────────────────────────────────────────────────────────────

_HELP_TEXT = """\
SimGenerator Help
=================

PURPOSE
  SimGenerator creates randomised convoy scenario CSV files for
  ConvoySIM Stage A testing.  Each scenario encodes a velocity
  profile, identification-loss events, and optionally a FORT
  (emergency stop) event.


GENERATE TAB — PARAMETERS
  Scenario Duration (s)
    Total length of each scenario in seconds.  Events are distributed
    across this window.  Typical value: 120 s.

  Maximum Events
    Upper bound on the number of events per scenario.  The actual count
    may be lower when timing constraints cannot all be satisfied.

  Minimum Event Separation (s)
    Every event must be separated from its neighbours by at least this
    many seconds.  Lower values allow denser event packing.

  Number of Scenarios
    How many CSV files to produce in one batch.

  Random Seed
    An integer that initialises the random number generator.

    • Same seed + same settings → identical scenarios every run.
      Use this to reproduce a specific batch, share results, or
      compare two parameter sets on the same "random" draw.
    • Any whole number is valid: 0, 1, 42, 9999, -7, etc.
    • Leave blank for a fresh random batch each time (no seed).

  Output Root Folder
    The root directory under which each generation run is saved.
    Every run automatically creates a new sub-folder named
    DDMMYYYY_HHMM/ inside this root, so successive runs never
    overwrite each other.  Leave blank to use a folder called
    Scene_Gen/ in the current working directory.


SCENARIO NAMING
  Format:  {trucks}T_{velocity}_{gap}_{losses}_{fort}ES
  Example: 3T_hV_mG_idL2qs_0ES

    3T      — 3 trucks
    hV      — High Variable velocity (random jumps)
    mG      — Medium initial gap
    idL2qs  — 2 Quick-Short identification losses (~15 s each)
    0ES     — No FORT event  (1ES = FORT present)


VELOCITY TYPES
  nV  Nominal        Constant speed throughout scenario
  mV  Med. Variable  ±10 % random walk around nominal speed
  hV  High Variable  Random jumps across full speed range
  hB  Hard Brake     Constant speed then sharp deceleration


IDENTIFICATION LOSS TYPES
  qs  Quick-Short     ~15 s loss/resume cycle
  sl  Slow            ~60 s loss/resume cycle
  fv  Freq. Variant   ~30 s loss/resume cycle


SCENARIOS TAB
  Click a scenario name in the list to load its details and data table.

  Editing
    Double-click any cell in the data table to edit it in-place.
    Press Enter or Tab to confirm, Escape to discard.

  Rows
    "+ Add Row"    — inserts a blank row after the selection.
    "− Remove Row" — deletes the selected row.

  Saving
    "Save"    — overwrites the original exported CSV file.
    "Save As" — writes to a new file you choose.

  Opening existing scenarios
    Use File → Open Scenarios from Folder… to browse a folder of
    CSV files and view them in the list (metadata display only;
    full round-trip editing requires regeneration).
"""


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    root = tk.Tk()
    SimGeneratorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
