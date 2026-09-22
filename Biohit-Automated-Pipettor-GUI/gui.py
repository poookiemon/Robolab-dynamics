import ttkbootstrap as ttk
import os
from scipy.optimize import curve_fit
from tkinter import simpledialog
import tkinter as tk # Ensure this is here from our last fix
from ttkbootstrap.dialogs import Messagebox
import numpy as np
import matplotlib.pyplot as plt
import string
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.widgets import Button
from tkinter import filedialog
from scipy.ndimage import minimum_filter1d

class GUI:
    def __init__(self, master=None, plate_rows: int = 8, plate_columns: int = 6):
        if master:
            # Embedded Mode: Act as a Frame inside the LIMS tab
            self.gui = ttk.Frame(master)
            self.gui.pack(fill="both", expand=True)
            self.gui_theme_hex = "#2b3e50"  # Match superhero theme background
        else:
            # Standalone Mode: Act as a full Window
            self.gui = ttk.Window(title="Analyze measurement", themename="superhero")
            self.gui.geometry("1920x1080")
            self.gui_theme_hex = self.gui.style.colors.bg

        self.wells = plate_rows * plate_columns

        self.rows_var = ttk.IntVar(value=10)
        self.height_spacing_var = ttk.DoubleVar(value=1.4)
        self.min_freq_var = ttk.DoubleVar(value=1.2)
        self.smooth_var = ttk.IntVar(value=3)

        self.start_idx = 0
        self.mouse_inside_plot = False
        self.zoom_active = False

        self.gui.rowconfigure(0, weight=0, minsize=60)
        self.gui.rowconfigure(1, weight=1)
        self.gui.columnconfigure(0, weight=0, minsize=120)
        self.gui.columnconfigure(1, weight=1)
        self.gui.columnconfigure(3, weight=0, minsize=20)

        self.header_frame = ttk.Frame(self.gui)
        self.header_frame.grid(row=0, column=0, columnspan=4, sticky="nsew", pady=20)
        self.header_frame.columnconfigure(0, weight=0)
        self.header_frame.columnconfigure(1, weight=1)
        self.header_frame.rowconfigure(0, weight=2)

        self.left_panel = ttk.Frame(self.gui)
        self.left_panel.grid(row=1, column=0, sticky="ns")

        for i in range(9):
            self.left_panel.rowconfigure(i, weight=1)
        self.left_panel.columnconfigure(0, weight=1)
        self.left_panel.columnconfigure(1, weight=2)
        self.left_panel.columnconfigure(2, weight=1)

        ttk.Button(self.header_frame, text="CSV", command=self.load_file).grid(
            row=0, column=0, pady=5, padx=5
        )

        # --- NEW UI ELEMENT ---
        ttk.Button(self.header_frame, text="Generate Ca2+ Curve", style="warning.TButton",
                   command=self.generate_calcium_curve).grid(
            row=0, column=1, pady=5, padx=5
        )

        ttk.Label(self.left_panel, text="Rows:", font=("Helvetica", 16), anchor="c").grid(row=1, column=0, sticky="new", columnspan=3)
        self.rows_entry = ttk.Entry(self.left_panel, textvariable=self.rows_var, justify="center")
        self.rows_entry.grid(row=1, column=1, sticky="ew")
        self.rows_entry.bind("<Return>", self.on_rows_changed)
        ttk.Button(self.left_panel, text="<", command=lambda: [self.rows_var.set(max(1, self.rows_var.get() - 1)), self.on_rows_changed(None)]).grid(row=1, column=0, sticky="ew", padx=(8, 0))
        ttk.Button(self.left_panel, text=">", command=lambda: [self.rows_var.set(min(48, self.rows_var.get() + 1)), self.on_rows_changed(None)]).grid(row=1, column=2, sticky="ew", padx=(0, 8))

        ttk.Label(self.left_panel, text="Max Frq in hz", font=("Helvetica", 16), anchor="c").grid(row=2, column=0, sticky="new", padx=8, columnspan=3)
        self.distance_entry = ttk.Entry(self.left_panel, textvariable=self.min_freq_var, justify="center")
        self.distance_entry.grid(row=2, column=1, sticky="ew")
        self.distance_entry.bind("<Return>", self.on_distance_entry)
        ttk.Button(self.left_panel, text="<", command=lambda: [self.min_freq_var.set(round(max(0.1, self.min_freq_var.get() - 0.1), 1)), self.on_distance_entry(None)]).grid(row=2, column=0, sticky="ew", padx=(8, 0))
        ttk.Button(self.left_panel, text=">", command=lambda: [self.min_freq_var.set(round(self.min_freq_var.get() + 0.1, 1)), self.on_distance_entry(None)]).grid(row=2, column=2, sticky="ew", padx=(0, 8))

        ttk.Label(self.left_panel, text="Smooth", font=("Helvetica", 16), anchor="c").grid(row=3, column=0, sticky="new", padx=8, columnspan=3)
        self.smooth_entry = ttk.Entry(self.left_panel, textvariable=self.smooth_var, justify="center")
        self.smooth_entry.grid(row=3, column=1, sticky="ew")
        self.smooth_entry.bind("<Return>", self.on_smooth_changed)
        ttk.Button(self.left_panel, text="<", command=lambda: [self.smooth_var.set(max(1, self.smooth_var.get() - 1)), self.on_smooth_changed(None)]).grid(row=3, column=0, sticky="ew", padx=(8, 0))
        ttk.Button(self.left_panel, text=">", command=lambda: [self.smooth_var.set(min(99, self.smooth_var.get() + 1)), self.on_smooth_changed(None)]).grid(row=3, column=2, sticky="ew", padx=(0, 8))

        self.plot_frame = ttk.Frame(self.gui)
        self.plot_frame.grid(row=1, column=1, sticky="nsew")
        self.plot_frame.rowconfigure(0, weight=1)
        self.plot_frame.columnconfigure(0, weight=1)

        self.scrollbar = ttk.Scrollbar(self.gui, orient="vertical", command=self.on_scrollbar)
        self.scrollbar.grid(row=0, column=3, sticky="ns", rowspan=3)

        self.gui.bind_all("<MouseWheel>", self._on_mousewheel)
        self.row_window: dict[int, RowWindow] = {}

    def load_file(self) -> None:
        path = filedialog.askopenfilename(title="CSV auswählen", filetypes=[("CSV Dateien", "*.csv")])
        if not path: return
        self.data = np.loadtxt(path, delimiter=",")
        self.create_plots()

    def get_data(self) -> tuple[np.ndarray, np.ndarray]:
        return self.data[:, 0], self.data[:, 1:]

    def create_plots(self) -> None:
        time, values = self.get_data()
        if hasattr(self, 'canvas'):
            self.canvas.get_tk_widget().destroy()
            plt.close(self.fig)

        for rw in self.row_window.values():
            rw.window.destroy()
        self.row_window = {}

        rows = self.rows_var.get()
        self.fig, self.axes = plt.subplots(rows, 1, figsize=(1, 1))
        self.fig.subplots_adjust(top=0.98, bottom=0.02, left=0.10, right=0.90, hspace=0)
        self.fig.patch.set_facecolor(self.gui_theme_hex)

        if not isinstance(self.axes, np.ndarray):
            self.axes = [self.axes]

        self.canvas = FigureCanvasTkAgg(self.fig, master=self.plot_frame)
        widget = self.canvas.get_tk_widget()
        widget.grid(row=0, column=0, sticky="nsew")
        widget.config(width=1, height=1)

        self.canvas.mpl_connect("motion_notify_event", self.on_hover)
        self.canvas.mpl_connect("figure_leave_event", self.on_leave)
        self.canvas.mpl_connect("scroll_event", self.on_zoom)

        for row_idx in range(self.wells):
            row_letter = string.ascii_uppercase[row_idx // 6]
            col_number = (row_idx % 6) + 1
            name = f"{row_letter}{col_number}"
            # Pass the top-level parent to avoid rendering bugs in embedded mode
            self.row_window[row_idx] = RowWindow(row_idx, name, time, values[:, row_idx], gui=self.gui.winfo_toplevel())

        self.update_plots()

    def update_buttons(self) -> None:
        if hasattr(self, '_btn_axes'):
            for bax in self._btn_axes: bax.remove()
        self._btn_axes = []
        self._btn_objects = []

        rows = self.rows_var.get()
        for i in range(rows):
            data_idx = self.start_idx + i
            if data_idx >= self.wells: break
            ax = self.axes[i]
            pos = ax.get_position()
            btn_ax = self.fig.add_axes([0.89, pos.y0, 0.10, pos.height])
            self._btn_axes.append(btn_ax)
            btn = Button(btn_ax, self.row_window[data_idx].row_name)
            btn.on_clicked(lambda _, idx=data_idx: self.open_row(idx))
            self._btn_objects.append(btn)
        self.canvas.draw_idle()

    def on_zoom(self, event) -> None:
        if event.inaxes is None: return
        self.zoom_active = True
        base_scale = 1.2
        scale = 1 / base_scale if event.button == "up" else base_scale if event.button == "down" else None
        if scale is None: return
        xlim = event.inaxes.get_xlim()
        xdata = event.xdata
        if xdata is None: return
        x_range = (xlim[1] - xlim[0]) * scale
        relx = (xdata - xlim[0]) / (xlim[1] - xlim[0])
        event.inaxes.set_xlim([xdata - x_range * relx, xdata + x_range * (1 - relx)])
        self.canvas.draw_idle()

    def on_hover(self, event) -> None:
        self.mouse_inside_plot = True
        if self.zoom_active: return
        for ax in self.axes: ax.set_alpha(0.3)
        if event.inaxes: event.inaxes.set_alpha(1.0)
        self.canvas.draw_idle()

    def on_leave(self, event) -> None:
        self.mouse_inside_plot = False
        for ax in self.axes: ax.set_alpha(1.0)
        self.canvas.draw_idle()

    def update_plots(self) -> None:
        if hasattr(self, '_metric_texts'):
            for txt in self._metric_texts: txt.remove()
        self._metric_texts = []

        for i, ax in enumerate(self.axes):
            ax.clear()
            data_idx = self.start_idx + i
            if data_idx >= self.wells: continue

            metrics = self.row_window[data_idx].plot(ax, min_frq=self.min_freq_var.get(), smooth_buffer=self.smooth_var.get())
            pos = ax.get_position()
            y_center = pos.y0 + pos.height / 2

            freq, mean_contraction = metrics["freq"], metrics["mean_contraction"]
            label = f"{freq:.2f} Hz\n{mean_contraction:.1f} Force[%]"

            txt = self.fig.text(0.005, y_center, label, va="center", ha="left", fontsize=9, color="white", linespacing=1.6)
            self._metric_texts.append(txt)

        self.fig.supxlabel("Time in s", fontsize=10)
        self.canvas.draw_idle()
        self.update_buttons()
        self.update_scrollbar()

    def update_scrollbar(self) -> None:
        total = self.wells - self.rows_var.get()
        if total <= 0:
            self.scrollbar.set(0, 1)
            return
        start = self.start_idx / total
        end = (self.start_idx + self.rows_var.get()) / self.wells
        self.scrollbar.set(start, end)

    def _on_mousewheel(self, event) -> None:
        if not hasattr(self, 'axes'): return
        focused = self.gui.focus_get()
        if focused is not None and str(focused.winfo_toplevel()) != str(self.gui.winfo_toplevel()): return
        if self.mouse_inside_plot: return
        direction = int(-event.delta / 120) if event.delta else 0
        self.start_idx += direction
        self.start_idx = max(0, min(self.start_idx, self.wells - self.rows_var.get()))
        self.update_plots()

    def on_scrollbar(self, *args) -> None:
        if not hasattr(self, 'axes'): return
        if args[0] == "moveto":
            fraction = float(args[1])
            max_start = self.wells - self.rows_var.get()
            self.start_idx = int(fraction * max_start)
        self.start_idx = max(0, min(self.start_idx, self.wells - self.rows_var.get()))
        self.update_plots()

    def open_row(self, idx: int) -> None:
        self.row_window[idx].open(min_frq=self.min_freq_var.get(), smooth_buffer=self.smooth_var.get())

    def on_rows_changed(self, event) -> None:
        if self.rows_var.get() < 1: self.rows_var.set(1)
        if self.rows_var.get() > 48: self.rows_var.set(48)
        try: self.create_plots()
        except AttributeError: pass

    def on_distance_entry(self, event) -> None:
        if self.min_freq_var.get() < 0.1: self.min_freq_var.set(0.1)
        try: self.update_plots()
        except AttributeError: pass

    def on_smooth_changed(self, event=None) -> None:
        if self.smooth_var.get() < 1: self.smooth_var.set(1)
        try: self.update_plots()
        except AttributeError: pass

    def generate_calcium_curve(self) -> None:
        # 1. Target the pre-calculated FOC48 peak files
        file_paths = filedialog.askopenfilenames(
            title="Select '*peak_forces.csv' or standard '.csv' files",
            filetypes=[("CSV Files", "*.csv")]
        )
        if not file_paths:
            return
            
        num_files = len(file_paths)

        file_paths = sorted(file_paths)
        print(f"Ingesting {num_files} target files: {[os.path.basename(p) for p in file_paths]}")

        # 2. Acquire concentration gradient parameters dynamically
        default_concs = ", ".join([str(0.2 * (i+1)) for i in range(num_files)])
        conc_str = simpledialog.askstring(
            "Concentration Gradient",
            f"You selected {num_files} files.\nEnter {num_files} Calcium concentrations (mM) separated by commas:\n(e.g., {default_concs})",
            initialvalue=default_concs
        )
        if not conc_str: return

        try:
            concentrations = np.array([float(x.strip()) for x in conc_str.split(',')])
            if len(concentrations) != num_files: 
                raise ValueError
        except ValueError:
            import tkinter.messagebox as messagebox
            messagebox.showerror("Parsing Error", f"Invalid input. You must enter exactly {num_files} numeric values separated by commas.")
            return

        force_responses = []

        # 3. Execute array extraction and noise filtration
        for idx, path in enumerate(file_paths):
            try:
                data = np.genfromtxt(path, delimiter=',')
                # Isolate strict positive force integers, rejecting NaN hardware outputs
                valid_forces = data[~np.isnan(data) & (data > 0)]
                step_average = np.mean(valid_forces) if valid_forces.size > 0 else 0.0
                force_responses.append(step_average)
                print(f"File {idx + 1} Mean Force Extracted: {step_average:.2f}")
            except Exception as e:
                print(f"Extraction failure on file {path}: {e}")
                force_responses.append(0.0)

        force_responses = np.array(force_responses)

        # 4. Execute SciPy regression bounds
        def hill_equation(C, E_max, EC50, h):
            return (E_max * (C ** h)) / ((EC50 ** h) + (C ** h))

        try:
            p0 = [max(force_responses) if max(force_responses) > 0 else 1.0, np.median(concentrations), 1.0]
            popt, _ = curve_fit(hill_equation, concentrations, force_responses, p0=p0, bounds=(0, [np.inf, np.inf, 5]))
            E_max, EC50, h = popt
            print(f"Regression converged. E_max: {E_max:.2f}, EC50: {EC50:.2f}, h: {h:.2f}")
        except Exception as e:
            Messagebox.show_error(f"Hill regression failed to converge: {e}", "Mathematical Error")
            return

        # 5. Render kinematic data plot (FIXED: Garbage Collection & Z-Ordering)
        self.curve_win = tk.Toplevel(self.gui.winfo_toplevel())
        self.curve_win.title("Calcium Dose-Response Kinematics")
        self.curve_win.geometry("800x600")

        # Force the window to the absolute front of the screen
        self.curve_win.attributes('-topmost', True)
        self.curve_win.focus_force()

        fig, ax = plt.subplots(figsize=(8, 6))
        ax.plot(concentrations, force_responses, 'ro', markersize=8, label='Empirical Data (FOC48 Mean Peak)')
        c_smooth = np.linspace(min(concentrations) * 0.5, max(concentrations) * 1.1, 100)
        ax.plot(c_smooth, hill_equation(c_smooth, E_max, EC50, h), 'b-', linewidth=2,
                label=f'Hill Fit (EC50: {EC50:.2f} mM)')
        ax.set_xscale('log')
        ax.set_xlabel('Calcium Concentration (mM) [Logarithmic]')
        ax.set_ylabel('Mean Peak Force')
        ax.set_title('Automated FOC48 Calcium Dose-Response Plot')
        ax.legend()
        ax.grid(True, which="both", ls="--", alpha=0.5)

        # Lock the canvas into memory with "self." so Python doesn't delete it
        self.curve_canvas = FigureCanvasTkAgg(fig, master=self.curve_win)
        self.curve_canvas.get_tk_widget().pack(fill="both", expand=True)
        self.curve_canvas.draw()

        # Release the top-most lock after 1 second so it doesn't block other applications
        # Release the top-most lock after 1 second so it doesn't block other applications
        self.curve_win.after(1000, lambda: self.curve_win.attributes('-topmost', False))

class RowWindow:
    def __init__(self, row_idx: int, row_name: str, time: np.ndarray, values: np.ndarray, gui):
        self.row_idx, self.row_name, self.time, self.values = row_idx, row_name, time, values
        self.window = tk.Toplevel(master=gui)
        self.window.geometry("1920x720")
        self.window.title(self.row_name)
        self.window.withdraw()
        self.detail_fig = None
        self.detail_canvas = None
        self.detail_ax = None

    def smooth(self, values: np.ndarray, buffer: int) -> np.ndarray:
        if buffer < 2: return values.copy()
        if buffer % 2 == 0: buffer += 1
        half = buffer // 2
        kernel = np.ones(buffer) / buffer
        convolved = np.convolve(values, kernel, mode='valid')
        result = values.copy()
        result[half: len(values) - half] = convolved
        return result

    def running_max(self, values: np.ndarray, window_sec: float, dt: float) -> np.ndarray:
        from scipy.ndimage import maximum_filter1d
        window_samples = max(1, int(window_sec / dt))
        if window_samples % 2 == 0: window_samples += 1
        return maximum_filter1d(values, size=window_samples)

    def find_peaks(self, values: np.ndarray, min_frq: float, dt: float) -> tuple[np.ndarray, np.ndarray]:
        min_spacing = int((1.0 / min_frq) / dt)
        kernel_size = 2 * min_spacing + 1
        window_min = minimum_filter1d(values, size=kernel_size)
        candidates = np.where(values == window_min)[0]
        if len(candidates) == 0: return np.array([], dtype=int), np.array([])
        peaks = [candidates[0]]
        for idx in candidates[1:]:
            if idx - peaks[-1] >= min_spacing: peaks.append(idx)
            elif values[idx] < values[peaks[-1]]: peaks[-1] = idx
        peak_idx = np.array(peaks)
        return peak_idx, values[peak_idx]

    def compute_metrics(self, min_frq: float, smooth_buffer: int, run_max_window_sec: float = 2.0) -> dict:
        dt = float(self.time[1] - self.time[0])
        smoothed = self.smooth(self.values, smooth_buffer)
        run_max = self.running_max(smoothed, run_max_window_sec, dt)
        peak_idx, peak_val = self.find_peaks(smoothed, min_frq, dt)
        run_max_at_peaks = run_max[peak_idx]
        peak_height = run_max_at_peaks - peak_val
        with np.errstate(invalid='ignore', divide='ignore'):
            contraction = np.where(run_max_at_peaks > 0, peak_height / run_max_at_peaks * 100, 0.0)
        mean_contraction = float(np.mean(contraction)) if len(contraction) > 0 else 0.0
        if len(peak_idx) >= 2:
            t_peaks = self.time[peak_idx]
            rr_intervals = np.diff(t_peaks)
            freq = float(1.0 / np.mean(rr_intervals))
        else:
            freq = 0.0
        return dict(smoothed=smoothed, run_max=run_max, peak_idx=peak_idx, peak_val=peak_val, peak_height=peak_height, contraction=contraction, mean_contraction=mean_contraction, freq=freq)

    def plot(self, ax: plt.Axes, min_frq: float = 1.2, smooth_buffer: int = 3, show_y_labels: bool = False, metrics: dict | None = None) -> dict:
        if metrics is None: metrics = self.compute_metrics(min_frq, smooth_buffer)
        ax.plot(self.time, self.values, alpha=0.3, color="steelblue")
        ax.plot(self.time, metrics["smoothed"], color="steelblue")
        ax.plot(self.time, metrics["run_max"], color="gold", linewidth=1.2)
        ax.plot(self.time[metrics["peak_idx"]], metrics["peak_val"], "ro", markersize=4)
        ax.grid(True)
        ax.invert_yaxis()
        if not show_y_labels:
            ax.tick_params(left=False, labelleft=False)
        else:
            ax.set_xlabel("Time in s")
            ax.set_ylabel("Distance in pixel")
        return metrics

    def _make_zoom_handler(self, canvas: FigureCanvasTkAgg):
        def on_zoom(event):
            if event.inaxes is None: return
            base_scale = 1.2
            if event.button == "up": scale = 1 / base_scale
            elif event.button == "down": scale = base_scale
            else: return
            ax = event.inaxes
            xlim = ax.get_xlim()
            xdata = event.xdata
            if xdata is None: return
            x_range = (xlim[1] - xlim[0]) * scale
            relx = (xdata - xlim[0]) / (xlim[1] - xlim[0])
            ax.set_xlim([xdata - x_range * relx, xdata + x_range * (1 - relx)])
            canvas.draw_idle()
        return on_zoom

    def open(self, min_frq: float = 1.2, smooth_buffer: int = 3) -> None:
        if self.window.winfo_ismapped():
            self.window.lift()
            return
        if self.detail_fig is None:
            self.detail_fig, self.detail_ax = plt.subplots(figsize=(16, 4))
            self.detail_fig.subplots_adjust(left=0.05, right=0.98, top=0.95, bottom=0.1)
            self.detail_canvas = FigureCanvasTkAgg(self.detail_fig, master=self.window)
            self.detail_canvas.get_tk_widget().pack(fill="both", expand=True)
            self.detail_canvas.mpl_connect("scroll_event", self._make_zoom_handler(self.detail_canvas))
        self.window.protocol("WM_DELETE_WINDOW", self.window.withdraw)
        self.detail_ax.clear()
        self.plot(self.detail_ax, min_frq=min_frq, smooth_buffer=smooth_buffer, show_y_labels=True)
        self.detail_canvas.draw()
        self.window.deiconify()
        self.window.lift()

# --- SAFETY LOCK: Only execute if run standalone ---
if __name__ == "__main__":
    gui = GUI()
    root = gui.gui
    root.mainloop()