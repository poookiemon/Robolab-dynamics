import re

with open('/Users/shri/Robolab-dynamics/Biohit-Automated-Pipettor-GUI/gui.py', 'r') as f:
    code = f.read()

# 1. Add the Save Plot button to the header
old_header = """        ttk.Button(self.header_frame, text = "Heatmap", command=self.heat_map_callback).grid(
            row = 0, column = 1, pady= 5, padx = 5, sticky = "nsew"
        )"""

new_header = """        ttk.Button(self.header_frame, text = "Heatmap", command=self.heat_map_callback).grid(
            row = 0, column = 1, pady= 5, padx = 5, sticky = "nsew"
        )

        ttk.Button(self.header_frame, text="Save Plot", command=self.save_plot).grid(
            row=0, column=2, pady=5, padx=5, sticky="nsew"
        )"""

if old_header in code:
    code = code.replace(old_header, new_header)


# 2. Add the save_plot method
save_method = """
    def save_plot(self) -> None:
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
            messagebox.showerror("Error", f"Failed to save plot:\\n{e}")

    def get_data(self) -> tuple[np.ndarray, np.ndarray]:"""

if "    def get_data(self) -> tuple[np.ndarray, np.ndarray]:" in code:
    code = code.replace("    def get_data(self) -> tuple[np.ndarray, np.ndarray]:", save_method)


with open('/Users/shri/Robolab-dynamics/Biohit-Automated-Pipettor-GUI/gui.py', 'w') as f:
    f.write(code)

print("PATCH SUCCESSFUL")
