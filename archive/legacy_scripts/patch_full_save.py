import re

with open('/Users/shri/Robolab-dynamics/Biohit-Automated-Pipettor-GUI/gui.py', 'r') as f:
    code = f.read()

old_save = """    def save_plot(self) -> None:
        if not self.loaded_file:
            from tkinter import messagebox
            messagebox.showwarning("No Data", "Please load a CSV file first.")
            return
            
        filepath = filedialog.asksaveasfilename(
            title="Save Plot As",
            defaultextension=".png",
            filetypes=[("PNG Image", "*.png"), ("PDF Document", "*.pdf")],
            initialfile=f"{self.filename}_plot.png"
        )
        if not filepath:
            return
            
        try:
            self.fig.savefig(filepath, dpi=300, bbox_inches='tight')
            from tkinter import messagebox
            messagebox.showinfo("Success", f"Plot successfully saved to:\\n{filepath}")
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("Error", f"Failed to save plot:\\n{e}")"""

new_save = """    def save_plot(self) -> None:
        if not self.loaded_file:
            from tkinter import messagebox
            messagebox.showwarning("No Data", "Please load a CSV file first.")
            return
            
        filepath = filedialog.asksaveasfilename(
            title="Save Plot As",
            defaultextension=".png",
            filetypes=[("PNG Image", "*.png"), ("PDF Document", "*.pdf")],
            initialfile=f"{self.filename}_full_plate.png"
        )
        if not filepath:
            return
            
        try:
            self.gui.config(cursor="wait")
            self.gui.update()
            
            import matplotlib.pyplot as plt
            import numpy as np
            
            # Create a massive hidden figure for ALL wells so they aren't limited to the GUI scroll view
            export_fig, export_axes = plt.subplots(self.wells, 1, figsize=(12, 1.0 * self.wells))
            export_fig.subplots_adjust(top=0.99, bottom=0.01, left=0.1, right=0.95, hspace=0.3)
            
            if not isinstance(export_axes, np.ndarray):
                export_axes = [export_axes]
                
            min_frq = self.min_freq_var.get()
            smooth_buffer = self.smooth_var.get()
            
            # Draw all wells
            for idx in range(self.wells):
                ax = export_axes[idx]
                if idx in self.row_window:
                    rw = self.row_window[idx]
                    rw.plot(ax, min_frq=min_frq, smooth_buffer=smooth_buffer, show_y_labels=False)
                    ax.set_ylabel(rw.row_name, rotation=0, labelpad=20, ha='right', va='center', fontweight='bold', fontsize=12)
                    
            export_fig.savefig(filepath, dpi=150, bbox_inches='tight')
            plt.close(export_fig)
            
            self.gui.config(cursor="")
            from tkinter import messagebox
            messagebox.showinfo("Success", f"Full 48-well plate successfully saved to:\\n{filepath}")
        except Exception as e:
            self.gui.config(cursor="")
            from tkinter import messagebox
            messagebox.showerror("Error", f"Failed to save plot:\\n{e}")"""

if old_save in code:
    code = code.replace(old_save, new_save)
    with open('/Users/shri/Robolab-dynamics/Biohit-Automated-Pipettor-GUI/gui.py', 'w') as f:
        f.write(code)
    print("PATCH SUCCESSFUL")
else:
    print("FAILED TO MATCH")
