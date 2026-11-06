import re

with open('/Users/shri/Robolab-dynamics/Biohit-Automated-Pipettor-GUI/gui.py', 'r') as f:
    code = f.read()

old_header = """        ttk.Button(self.header_frame, text="Save Plot", command=self.save_plot).grid(
            row=0, column=2, pady=5, padx=5, sticky="nsew"
        )"""

new_header = """        ttk.Button(self.header_frame, text="Save Plot", command=self.save_plot).grid(
            row=0, column=2, pady=5, padx=5, sticky="nsew"
        )
        
        ttk.Button(self.header_frame, text="Export HTML", command=self.save_plotly).grid(
            row=0, column=3, pady=5, padx=5, sticky="nsew"
        )"""

if old_header in code:
    code = code.replace(old_header, new_header)

old_save_plot = """    def save_plot(self) -> None:"""

new_save_plotly = """    def save_plotly(self) -> None:
        if not self.loaded_file:
            from tkinter import messagebox
            messagebox.showwarning("No Data", "Please load a CSV file first.")
            return
            
        from tkinter import filedialog
        filepath = filedialog.asksaveasfilename(
            title="Export Interactive HTML",
            defaultextension=".html",
            filetypes=[("HTML File", "*.html")],
            initialfile=f"{self.filename}_interactive.html"
        )
        if not filepath:
            return
            
        try:
            self.gui.config(cursor="wait")
            self.gui.update()
            
            from backend_plotly import generate_interactive_html
            time_arr, values_arr = self.get_data()
            generate_interactive_html(time_arr, values_arr, filepath, title=f"FOC48 Kinetics: {self.filename}")
            
            self.gui.config(cursor="")
            from tkinter import messagebox
            messagebox.showinfo("Success", f"Interactive HTML successfully exported to:\\n{filepath}")
        except Exception as e:
            self.gui.config(cursor="")
            from tkinter import messagebox
            messagebox.showerror("Error", f"Failed to export HTML:\\n{e}")

    def save_plot(self) -> None:"""

if old_save_plot in code:
    code = code.replace(old_save_plot, new_save_plotly)

with open('/Users/shri/Robolab-dynamics/Biohit-Automated-Pipettor-GUI/gui.py', 'w') as f:
    f.write(code)
print("PATCH SUCCESSFUL")

