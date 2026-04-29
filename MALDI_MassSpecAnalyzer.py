import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import tkinter.font as tkfont
import pandas as pd
import sys
import os
import webbrowser
import re
from scipy.signal import savgol_filter


# Matplotlib Imports
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

# Custom Toolbar
class CustomToolbar(NavigationToolbar2Tk):
    toolitems = [t for t in NavigationToolbar2Tk.toolitems if 
                 t[0] not in ('Subplots', 'Customize')] 
    def __init__(self, canvas, window, app_instance):
        self.app = app_instance 
        super().__init__(canvas, window)
    def home(self, *args, **kwargs):
        super().home(*args, **kwargs)
        if hasattr(self.app, 'current_spec') and self.app.current_spec is not None:
            max_i = self.app.current_spec['intensity'].max()
            self.app.ax_main.set_ylim(0, max_i * 1.1)
        if hasattr(self.app, 'redraw_all_active_series'):
            self.app.redraw_all_active_series()

class MonomerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("MALDI Mass Spec Analyzer")
        self.root.geometry("1550x850")
        
        self.root.bind("<Delete>", lambda e: self.remove_last_series())

        # 1. Styles
        self.style = ttk.Style()
        self.style.configure("Treeview", rowheight=28, font=('Arial', 10))
        self.style.configure("Treeview.Heading", font=('Arial', 10, 'bold'))
        self.style.configure("Treeview", anchor="center")

        if getattr(sys, 'frozen', False):
            base_path = os.path.dirname(sys.executable)
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
            
        self.ref_file = os.path.join(base_path, "structures.xlsx")
        
        if not os.path.exists(self.ref_file):
            from tkinter import messagebox
            messagebox.showerror("Datei fehlt", 
                f"Konnte '{self.ref_file}' nicht finden!\n\n"
                "Bitte legen Sie 'structures.xlsx' in denselben Ordner wie die Programm-Datei.")
            self.ref_data = None
        else:
            self.ref_data = self.load_reference_table(self.ref_file)

        #  GUI Layout 
        frame_top = tk.Frame(root, padx=10, pady=10)
        frame_top.pack(fill="x")

        # 1. Button Load
        self.btn_step1 = tk.Button(frame_top, text="1. Load Spectrum", command=self.load_dat_full, 
                                  bg="#d1e7ff", font=('Arial', 10, 'bold'))
        self.btn_step1.grid(row=0, column=0, padx=5)
        
        # 2. Label Select
        self.lbl_step2 = tk.Label(frame_top, text="2. Select m/z Region", font=('Arial', 10), padx=10)
        self.lbl_step2.grid(row=0, column=1)

        # 3. Smooth Slider
        smooth_frame = tk.LabelFrame(frame_top, text="Smooth (optional)", font=('Arial', 10))
        smooth_frame.grid(row=0, column=2, padx=10)
        
        self.smooth_scale = tk.Scale(smooth_frame, from_=2, to=51, orient="horizontal", 
                                     resolution=2, length=120, showvalue=True,
                                     command=self.auto_smooth) 
        self.smooth_scale.set(2) 
        self.smooth_scale.pack(side="left", padx=5)

        self.raw_spec = None 

        # 4. Peak Threshold Slider
        thresh_frame = tk.LabelFrame(frame_top, text="Peak Detection Threshold (%)", font=('Arial', 10))
        thresh_frame.grid(row=0, column=3, padx=10)
        
        self.threshold_scale = tk.Scale(thresh_frame, from_=1, to=99, orient="horizontal", 
                                        length=150, showvalue=True,
                                        command=lambda val: self.update_peak_markers())
        self.threshold_scale.set(30) # Default 30%
        self.threshold_scale.pack(padx=5, pady=2)

        # 7. Addukt Auswahl
        self.adduct_frame = tk.LabelFrame(frame_top, text="Adduct Ion", font=('Arial', 10))
        self.adduct_frame.grid(row=0, column=4, padx=10)
        
        self.adduct_map = {
            "None (0.0)": 0.0,
            "H+ (1.01)": 1.008,
            "Li+ (7.02)": 7.016,
            "NH4+ (18.03": 18.034,
            "Na+ (22.99)": 22.989,
            "K+ (39.10)": 39.098,
            "Ag+ (107.87)": 107.868,
            "Cs+ (132.91)": 132.905
        }
        
        self.combo_adduct = ttk.Combobox(self.adduct_frame, values=list(self.adduct_map.keys()), 
                                         width=12, state="readonly")
        self.combo_adduct.set("None (0.0)")
        self.combo_adduct.pack(padx=5, pady=2)
        
        self.combo_adduct.bind("<<ComboboxSelected>>", self.refresh_on_adduct_change)
        
        # Tolerance (Da) 
        tol_frame = tk.LabelFrame(frame_top, text="Match Tolerance (Da)", font=('Arial', 10))
        tol_frame.grid(row=0, column=5, padx=10)
        
        self.ent_tolerance = tk.Entry(tol_frame, width=8, font=('Arial', 10), justify='center')
        self.ent_tolerance.insert(0, "0.5")  # Default 0.5 Da
        self.ent_tolerance.pack(padx=5, pady=5)

        # 5. Button Analyze Zoom
        self.btn_step4 = tk.Button(frame_top, text="3. Analyze m/z Region", command=self.analyze_visible_range, 
                                  bg="#fff9c4", font=('Arial', 10, 'bold'))
        self.btn_step4.grid(row=0, column=6, padx=10)

        # Sensitivity 
        series_thresh_frame = tk.LabelFrame(frame_top, text="Series Sens. (%)", font=('Arial', 10))
        series_thresh_frame.grid(row=0, column=7, padx=10)
        
        self.ent_series_thresh = tk.Entry(series_thresh_frame, width=6, font=('Arial', 10), justify='center')
        self.ent_series_thresh.insert(0, "2.0")
        self.ent_series_thresh.pack(padx=5, pady=5)
        
        # 6. Monomer Select
        self.lbl_step5 = tk.Label(frame_top, text="4. Select Monomer from Table", font=('Arial', 10), padx=10)
        self.lbl_step5.grid(row=0, column=8)

        # 8. Click References
        self.lbl_step6 = tk.Label(frame_top, text="5. References", font=('Arial', 10), padx=10)
        self.lbl_step6.grid(row=0, column=9)

        # 9. Button Reset
        tk.Button(frame_top, text="Reset", command=self.reset_all, 
                  bg="#ffcdd2", font=('Arial', 10, 'bold')).grid(row=0, column=13, padx=20)
        # 10. Export
        self.btn_export = tk.Button(frame_top, text="Export Series", 
                                    command=self.export_series_to_columns, 
                                    bg="#c8e6c9", font=('Arial', 10, 'bold'))
        self.btn_export.grid(row=0, column=11, padx=10)

        # 11. Status text
        status_text = "Excel Ready" if self.ref_data is not None else "ERROR: structures.xlsx missing!"
        self.lbl_status = tk.Label(frame_top, text=status_text, fg="green" if self.ref_data is not None else "red")
        self.lbl_status.grid(row=0, column=14, padx=10)

        self.tree_frame = tk.Frame(root, height=200) 
        self.tree_frame.pack_propagate(False)
        self.tree_frame.pack(fill="x", padx=10, pady=5)
        
        self.columns = ("Monomer Unit", "Polymer", "Repeat Unit Mass", "Delta (exp)", "Match Tolerance (Da)", "Peak A", "Peak B", "References")
        self.tree = ttk.Treeview(self.tree_frame, columns=self.columns, show='headings')
        
        self.tree.tag_configure('hover', background='#e3f2fd')
        self.tree.bind("<Motion>", self.on_hover_motion)
        self.tree.bind("<Leave>", lambda e: self.tree.tk.call(self.tree, "tag", "remove", "hover"))

        self.scrollbar = ttk.Scrollbar(self.tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.scrollbar.set)
        
        for col in self.columns:
            self.tree.heading(col, text=col, anchor="center")
            self.tree.column(col, anchor="center", width=120, stretch=True)
        
        self.tree.tag_configure('has_link', background='#e1f5fe')
        self.tree.bind("<Double-1>", self.on_double_click)
        self.tree.bind("<<TreeviewSelect>>", self.on_select_row)

        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

        self.scrollbar.pack(side="right", fill="y")
        self.tree.pack(side="left", fill="both", expand=True)

        self.paned = tk.PanedWindow(root, orient="horizontal", sashrelief="raised", sashwidth=10, bg="gray")
        self.paned.pack(fill="both", expand=True, padx=5, pady=5)

        self.frame_left = tk.Frame(self.paned, bg="white", highlightthickness=1)
        self.frame_right = tk.Frame(self.paned, bg="white", highlightthickness=1)
        self.paned.add(self.frame_left, stretch="always")
        self.paned.add(self.frame_right, stretch="always")

        self.fig_main = Figure(figsize=(8, 6), dpi=100)
        self.ax_main = self.fig_main.add_subplot(111)
        self.ax_main.set_facecolor('#f8f9fa')
        self.ax_main.grid(True, linestyle=':', alpha=0.5, color='gray')
        
        self.canvas_main = FigureCanvasTkAgg(self.fig_main, master=self.frame_left)
        self.toolbar_main = CustomToolbar(self.canvas_main, self.frame_left, self)
        self.canvas_main.get_tk_widget().pack(side="top", fill="both", expand=True)

        self.fig_zoom = Figure(figsize=(5, 4), dpi=90)
        self.ax_zoom = self.fig_zoom.add_subplot(111)
        
        self.canvas_zoom = FigureCanvasTkAgg(self.fig_zoom, master=self.frame_right)
        self.canvas_zoom.get_tk_widget().pack(fill="both", expand=True)
        self.ax_zoom.set_facecolor('#f8f9fa')
        self.ax_zoom.grid(True, linestyle=':', alpha=0.5, color='gray')

        self.current_spec = None
        
        self.all_series_plots = {} 
        self.color_cycle = ['#00FF00', '#FF00FF', '#0000FF', '#FFA500', '#888888', '#ff0000', '#48EDDD', '#800080'] 
        self.color_index = 0
        self.series_scatter_objects = [] 

    def on_hover_motion(self, event):
        item = self.tree.identify_row(event.y)
        
        self.tree.tk.call(self.tree, "tag", "remove", "hover")
        
        if item:
            current_tags = list(self.tree.item(item, "tags"))
            if 'hover' not in current_tags:
                current_tags.append('hover')
                self.tree.item(item, tags=tuple(current_tags))

    
    def draw_filename_label(self):
        if hasattr(self, 'current_filename') and self.current_filename:
            self.ax_main.text(0.02, 0.96, f"File: {self.current_filename}", 
                              transform=self.ax_main.transAxes,
                              fontsize=9, color='darkblue', fontweight='bold',
                              verticalalignment='top', 
                              bbox=dict(facecolor='white', alpha=0.7, edgecolor='none'))


    def highlight_step(self, widget):
        widget.config(fg="gray", font=('Arial', 10, 'bold'))
        
    def _refresh_plot_decorations(self, ax):
        ax.set_facecolor('#f8f9fa') 
        ax.set_xlabel("m/z", fontsize=10)
        ax.set_ylabel("Intensity", fontsize=10)
        ax.grid(True, linestyle=':', alpha=0.5)
        
        ax.set_title("Press [DEL] to remove last series", 
                     fontsize=9, color='gray', loc='right', style='italic')

    def reset_all(self):
        self.analysis_results = {}
        if hasattr(self, 'series_data_storage'): self.series_data_storage = {}
        if hasattr(self, 'series_colors'): self.series_colors = {}
        
        self.tree.delete(*self.tree.get_children())
        
        self.ax_zoom.clear()
        self.canvas_zoom.draw()
        
        if self.raw_spec is not None:
            cur_xlim = self.ax_main.get_xlim()
            
            self.ax_main.clear()
            self.ax_main.plot(self.raw_spec['mz'], self.raw_spec['intensity'], color='black', lw=0.5)
            
            self.draw_filename_label()
            
            if hasattr(self, '_refresh_plot_decorations'):
                self._refresh_plot_decorations(self.ax_main)
            
            self.ax_main.set_xlim(cur_xlim)
            self.canvas_main.draw()

        self.lbl_status.config(text="Markers cleared. Spectrum kept.", fg="blue")
        for w in [self.btn_step1, self.lbl_step2, self.btn_step4, self.lbl_step5, self.lbl_step6]:
            try: w.config(fg="black", font=('Arial', 10))
            except: pass
            
    def patched_home(self):
        if hasattr(self, 'app') and self.app.current_spec is not None:
            df = self.app.current_spec
            
            x_min = df['mz'].min()
            x_max = df['mz'].max()
            self.app.ax_main.set_xlim(x_min, x_max)
            
            max_i = df['intensity'].max()
            self.app.ax_main.set_ylim(0, max_i * 1.1)
        else:
            self.old_home() 
        
        if hasattr(self.app, 'restore_all_series'):
            self.app.restore_all_series()
            
        if hasattr(self.app, '_refresh_plot_decorations'):
            self.app._refresh_plot_decorations(self.app.ax_main)
            
        self.app.canvas_main.draw_idle()

    def load_reference_table(self, filepath):
        if not os.path.exists(filepath): return None
        try:
            df = pd.read_excel(filepath)
            df.columns = df.columns.str.strip()
            return df
        except: return None

    def adjust_column_widths(self):
        font = tkfont.Font(family="Arial", size=10)
        for col in self.columns:
            max_w = font.measure(col) + 40
            for item in self.tree.get_children():
                val = self.tree.set(item, col)
                w = font.measure(str(val)) + 40
                if w > max_w: max_w = w
            self.tree.column(col, anchor="center", width=120, minwidth=100, stretch=True)


    def on_double_click(self, event):
        item = self.tree.identify_row(event.y)
        column = self.tree.identify_column(event.x)
        if item and column == "#8":
            content = str(self.tree.set(item, "References"))
            urls = re.findall(r'(https?://\S+)', content.replace(',', ' ').replace(';', ' '))
            for url in urls: webbrowser.open(url.strip())
            self.highlight_step(self.lbl_step6)

    def on_select_row(self, event):
        selected = self.tree.selection()
        if not selected or self.current_spec is None: return
        try:
            item = selected[0]
            pa = float(self.tree.set(item, "Peak A"))
            pb = float(self.tree.set(item, "Peak B"))
            monomer_m = float(self.tree.set(item, "Ref Mass"))
            label = self.tree.set(item, "Monomer Unit")

            self.update_zoom_plot(pa, pb, label, monomer_m)
            self.adduct_frame.config(fg="gray")
            self.highlight_step(self.lbl_step5)
            
        except Exception as e: 
            print(f"Update Error: {e}")

    def auto_smooth(self, val):
        if self.raw_spec is None: return

        try:
            cur_xlim = self.ax_main.get_xlim()
            cur_ylim = self.ax_main.get_ylim()

            window_size = int(val)
            if window_size % 2 == 0: window_size += 1
            
            from scipy.signal import savgol_filter
            self.current_spec = self.raw_spec.copy()
            p_order = min(2, window_size - 1)
            self.current_spec['intensity'] = savgol_filter(self.raw_spec['intensity'], window_size, p_order)
        
            self.ax_main.clear()
            self.ax_main.plot(self.current_spec['mz'], self.current_spec['intensity'], color='black', lw=0.5)
            
            self.draw_filename_label()
            
            self.ax_main.set_xlim(cur_xlim)
            self.ax_main.set_ylim(cur_ylim)

            self.redraw_all_active_series() 
            self.update_peak_markers(is_refresh=True) 
            
            if hasattr(self, '_refresh_plot_decorations'):
                self._refresh_plot_decorations(self.ax_main)
            
            if hasattr(self, 'last_zoom_params'):
                self.update_zoom_plot(*self.last_zoom_params)

            self.canvas_main.draw_idle()
            self.lbl_status.config(text=f"Live Smooth: {window_size} pts", fg="green")

        except Exception as e:
            print(f"Smooth Error: {e}")


    def update_zoom_plot(self, pa, pb, label_text, monomer_m):
        self.last_zoom_params = (pa, pb, label_text, monomer_m)
        
        ad_name = self.combo_adduct.get()
        ad_mass = self.adduct_map.get(ad_name, 0.0)
        ad_label = ad_name.split(" ")[0]

        search = 0.5
        def get_peak(mz_val):
            mask = (self.current_spec['mz'] >= mz_val - search) & (self.current_spec['mz'] <= mz_val + search)
            if not self.current_spec[mask].empty:
                p = self.current_spec[mask].loc[self.current_spec[mask]['intensity'].idxmax()]
                return p['mz'], p['intensity']
            return mz_val, 0

        pa_plot, ia = get_peak(pa)
        pb_plot, ib = get_peak(pb)

        res_a = (pa_plot - ad_mass) % monomer_m
        res_b = (pb_plot - ad_mass) % monomer_m
        
        self.ax_zoom.clear()
        self.ax_zoom.set_facecolor('#f8f9fa')
        self.ax_zoom.grid(True, linestyle=':', alpha=0.5, color='gray')
        self.ax_zoom.plot(self.current_spec['mz'], self.current_spec['intensity'], color='blue', lw=1.2)
        
        self.ax_zoom.scatter([pa_plot, pb_plot], [ia, ib], color='red', marker='v', s=80, zorder=7)
        self.ax_zoom.text(pa_plot, ia * 1.1, f"Resid. (-{ad_label}):\n{res_a:.2f} Da", 
                          ha='center', color='darkred', fontsize=10, fontweight='bold')
        self.ax_zoom.text(pb_plot, ib * 1.1, f"Resid. (-{ad_label}):\n{res_b:.2f} Da", 
                          ha='center', color='darkred', fontsize=10, fontweight='bold')
        
        mid_x, max_y = (pa_plot + pb_plot) / 2, max(ia, ib) * 1.5
        self.ax_zoom.annotate('', xy=(pa_plot, max_y), xytext=(pb_plot, max_y), 
                             arrowprops=dict(arrowstyle='<->', color='red', lw=1.5))
        self.ax_zoom.text(mid_x, max_y * 1.05, label_text, color='red', ha='center', fontweight='bold', fontsize=12)
        
        self.ax_zoom.set_xlim(min(pa_plot, pb_plot) - 50, max(pa_plot, pb_plot) + 50)
        self.ax_zoom.set_ylim(0, max_y * 1.7)
        self.ax_zoom.set_xlabel("m/z", fontweight='bold')
        self.ax_zoom.set_ylabel("Intensity", fontweight='bold')
        
        self.canvas_zoom.draw_idle()


    def redraw_all_active_series(self):

        if not hasattr(self, 'series_data_storage') or not self.series_data_storage:
            return
            
        for series_id, (mzs, ints) in self.series_data_storage.items():
            color = self.series_colors.get(series_id, 'green')
            
            self.ax_main.scatter(
                mzs, ints, 
                color=color, 
                s=40, 
                marker='o', 
                alpha=0.4, 
                edgecolor='black', 
                linewidth=0.5, 
                zorder=100 
            )
        self.canvas_main.draw_idle()


    def refresh_on_adduct_change(self, event=None):
        selected = self.tree.selection()
        if selected:
            self.on_select_row(None)

    def load_dat_full(self):
        file_path = filedialog.askopenfilename(filetypes=[("DAT files", "*.dat"), ("Text files", "*.txt")])
        if not file_path: return
        try:
            self.current_filename = os.path.basename(file_path)
            
            df = pd.read_csv(file_path, sep=r'\s+', comment='#', header=None, engine='python')
            df.columns = ['mz', 'intensity']
            
            self.raw_spec = df.copy() 
            self.current_spec = df.copy()
            self.draw_filename_label()
            self.ax_main.clear()
            self.ax_main.plot(df['mz'], df['intensity'], color='black', lw=0.5)
            self.draw_filename_label()
            self.ax_main.set_xlabel("m/z")
            self.ax_main.set_ylabel("Intensity")
            self.canvas_main.draw()
            self.highlight_step(self.btn_step1)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load: {e}")
        
            for scatter in self.all_series_plots.values():
                scatter.remove()
            self.all_series_plots.clear()
            self.color_index = 0

    def analyze_visible_range(self):
        if self.current_spec is None or self.ref_data is None:
            messagebox.showwarning("Warning", "Load Spectrum and Excel first!")
            return
            
        try:
            import numpy as np
            from scipy.signal import find_peaks

            xmin, xmax = self.ax_main.get_xlim()
            mask = (self.current_spec['mz'] >= xmin) & (self.current_spec['mz'] <= xmax)
            visible_data = self.current_spec[mask].copy()
            if len(visible_data) < 5: return

            thresh_f = self.threshold_scale.get() / 100.0
            try:
                tol_val = float(self.ent_tolerance.get().replace(',', '.'))
            except:
                tol_val = 0.5

            max_i = visible_data['intensity'].max()
            peaks, _ = find_peaks(visible_data['intensity'], prominence=max_i * thresh_f)
            if len(peaks) < 2: return
            
            p_mz = visible_data['mz'].iloc[peaks].tolist()
            p_int = visible_data['intensity'].iloc[peaks].tolist()

            cur_y = self.ax_main.get_ylim()

            self.ax_main.plot(self.current_spec['mz'], self.current_spec['intensity'], color='black', lw=0.5)
            self.ax_main.scatter(p_mz, p_int, color='red', marker='x', s=40, zorder=5)
            self.ax_main.set_xlim(xmin, xmax)
            self.ax_main.set_ylim(cur_y)
            self._refresh_plot_decorations(self.ax_main)
            self.canvas_main.draw()

            self.tree.delete(*self.tree.get_children())
            
            cols = self.ref_data.columns
            m_col = next((c for c in cols if "mass" in c.lower()), None)
            n_col = next((c for c in cols if "monomer" in c.lower()), None)
            p_col = next((c for c in cols if "polymer" in c.lower()), None)
            r_col = next((c for c in cols if "reference" in c.lower()), None)

            matches = []
            for i in range(len(p_mz)):
                for j in range(i + 1, len(p_mz)):
                    delta = abs(p_mz[j] - p_mz[i])

                    res = self.ref_data[(self.ref_data[m_col] - delta).abs() <= tol_val]
                    
                    for _, row in res.iterrows():
                        matches.append({
                            "name": str(row.get(n_col, 'Unknown')),
                            "poly": row.get(p_col, 'N/A'),
                            "d": delta,
                            "ref": row[m_col],
                            "err": abs(delta - row[m_col]),
                            "pa": p_mz[i],
                            "pb": p_mz[j],
                            "refs": str(row.get(r_col, '-'))
                        })

            if matches:
                unique_best = {}
                for m in matches:
                    if m['name'] not in unique_best or m['err'] < unique_best[m['name']]['err']:
                        unique_best[m['name']] = m
                
                sorted_res = sorted(unique_best.values(), key=lambda x: x['err'])
                
                for m in sorted_res:
                    self.tree.insert("", "end", values=(
                        m["name"], m["poly"], round(m["ref"],3),  round(m["d"],3),
                        round(m["err"],4), round(m["pa"],2), round(m["pb"],2), m["refs"]
                    ))

            self.lbl_status.config(text=f"Analyzed {len(p_mz)} peaks with {tol_val} Da tol.", fg="green")
            self.highlight_step(self.btn_step4)

        except Exception as e:
            print(f"Analysis Error: {e}")

    def highlight_series(self, start_mz, monomer_mass, series_id):
        if self.current_spec is None: return

        try:
            s_thresh_raw = self.ent_series_thresh.get().replace(',', '.')
            s_thresh_f = float(s_thresh_raw) / 100.0
        except:
            s_thresh_f = 0.01

        tol, series_mz, series_int = 1.0, [], []
        max_total_int = self.current_spec['intensity'].max()
        
        threshold_limit = max_total_int * s_thresh_f 

        for n in range(-50, 51):
            target = start_mz + (n * monomer_mass)
            mask = (self.current_spec['mz'] >= target - tol) & (self.current_spec['mz'] <= target + tol)
            
            if not self.current_spec[mask].empty:
                peak = self.current_spec[mask].loc[self.current_spec[mask]['intensity'].idxmax()]
                
                if peak['intensity'] >= threshold_limit:
                    series_mz.append(peak['mz'])
                    series_int.append(peak['intensity'])

        if series_mz:
            if not hasattr(self, 'series_data_storage'): self.series_data_storage = {}
            self.series_data_storage[series_id] = (series_mz, series_int)
            
            if not hasattr(self, 'series_colors'): self.series_colors = {}
            if series_id not in self.series_colors:
                self.series_colors[series_id] = self.color_cycle[len(self.series_colors) % len(self.color_cycle)]

            self.redraw_all_active_series()

    def update_peak_markers(self, is_refresh=False):
        if self.current_spec is None: return

        try:
            from scipy.signal import find_peaks
            xlim = self.ax_main.get_xlim()
            thresh = self.threshold_scale.get() / 100.0

            mask = (self.current_spec['mz'] >= xlim[0]) & (self.current_spec['mz'] <= xlim[1])
            vis = self.current_spec[mask]
            if vis.empty: return

            peaks, _ = find_peaks(vis['intensity'], prominence=vis['intensity'].max() * thresh)
            p_mz = vis['mz'].iloc[peaks]
            p_int = vis['intensity'].iloc[peaks]

            if not is_refresh:
                ylim = self.ax_main.get_ylim()
                self.ax_main.clear()
                self.draw_filename_label()
                self.ax_main.plot(self.current_spec['mz'], self.current_spec['intensity'], color='black', lw=0.5)
                self.ax_main.set_xlim(xlim)
                self.ax_main.set_ylim(ylim)
                self.redraw_all_active_series()

            self.ax_main.scatter(p_mz, p_int, color='red', marker='x', s=40, zorder=5)
            
            if not is_refresh:
                self.canvas_main.draw_idle()

        except Exception as e:
            print(f"Marker Error: {e}")

    def redraw_all_active_series(self):
        for obj in self.series_scatter_objects:
            try:
                obj.remove()
            except Exception:
                pass
        self.series_scatter_objects.clear()

        if not hasattr(self, 'series_data_storage') or not self.series_data_storage:
            if self.ax_main.get_legend(): self.ax_main.get_legend().remove()
            self.canvas_main.draw_idle()
            return

        def get_rm_value(s_id):
            try:
                import re
                match = re.search(r"RM:\s*([\d.]+)", s_id)
                return float(match.group(1)) if match else 0.0
            except: return 0.0

        sorted_keys = sorted(self.series_data_storage.keys(), key=get_rm_value)

        for series_id in sorted_keys:
            mzs, ints = self.series_data_storage[series_id]
            color = self.series_colors.get(series_id, 'red')
            clean_label = series_id.replace(" Da", "").strip()

            sc = self.ax_main.scatter(mzs, ints, color=color, marker='o', s=40, 
                                     edgecolors='black', linewidth=0.8,
                                     label=clean_label, zorder=10)
            self.series_scatter_objects.append(sc)

        leg = self.ax_main.legend(loc='upper right', fontsize='small', 
                                  title="Polymer Series (Sorted)", framealpha=0.5)
        if leg:
            leg.set_draggable(True)
        
        self.canvas_main.draw_idle()

        
    def on_tree_select(self, event):
        selection = self.tree.selection()
        if not selection: return
        
        item = self.tree.item(selection[0])
        values = item['values']
        
        try:
            series_name = str(values[1]) 
            monomer_m = float(str(values[2]).replace(',', '.')) 
            pa = float(str(values[5]).replace(',', '.'))         
            pb = float(str(values[6]).replace(',', '.'))         

            ad_mass = self.adduct_map.get(self.combo_adduct.get(), 0.0)
            residual = (pa - ad_mass) % monomer_m
            
            unique_id = f"{series_name} (RM: {residual:.1f} Da)"

            self.update_zoom_plot(pa, pb, unique_id, monomer_m)
            self.highlight_series(pa, monomer_m, unique_id)
            
        except Exception as e:
            print(f"Error in on_tree_select: {e}")

    def remove_last_series(self):
        if hasattr(self, 'series_data_storage') and self.series_data_storage:
            last_key = list(self.series_data_storage.keys())[-1]
            
            self.series_data_storage.pop(last_key)
            if hasattr(self, 'series_colors'):
                self.series_colors.pop(last_key, None)
            
            self.redraw_all_active_series()
            
            self.lbl_status.config(text=f"Removed: {last_key}", fg="orange")
        else:
            self.lbl_status.config(text="No series to remove", fg="red")

            
    def export_series_to_columns(self):
        if not hasattr(self, 'series_data_storage') or not self.series_data_storage:
            messagebox.showwarning("Export", "No series annotated yet!")
            return

        all_dfs = []
        for name, (mzs, ints) in self.series_data_storage.items():
            df_temp = pd.DataFrame({
                f"{name} m/z": [round(x, 4) for x in mzs],
                f"{name} Int": [round(y, 1) for y in ints]
            })
            all_dfs.append(df_temp)
        df_final = pd.concat(all_dfs, axis=1)

        file_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
            title="Save Series Columns"
        )

        if file_path:
            try:
                df_final.to_excel(file_path, index=False)
                messagebox.showinfo("Success", f"Exported {len(all_dfs)} series to columns.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed: {e}")




if __name__ == "__main__":
    root = tk.Tk()
    app = MonomerApp(root)
    root.mainloop()

