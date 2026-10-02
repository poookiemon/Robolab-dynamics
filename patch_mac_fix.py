import re

with open('Biohit-Automated-Pipettor-GUI/lims_master_gui.py', 'r') as f:
    code = f.read()

# Replace the threading update loop with Tkinter's root.after loop
old_loop = """        # Keep updating in a background loop
        def update_loop():
            while self.pv_plotter and not getattr(self.pv_plotter, '_closed', True):
                try:
                    self.pv_plotter.update()
                    time.sleep(0.05)
                except:
                    break
                    
        threading.Thread(target=update_loop, daemon=True).start()"""

new_loop = """        # Keep updating on the main GUI thread to prevent macOS Cocoa crash
        def update_loop():
            if self.pv_plotter and not getattr(self.pv_plotter, '_closed', True):
                try:
                    self.pv_plotter.update()
                    self.root.after(50, update_loop)
                except Exception:
                    pass
                    
        self.root.after(50, update_loop)"""

code = code.replace(old_loop, new_loop)

with open('Biohit-Automated-Pipettor-GUI/lims_master_gui.py', 'w') as f:
    f.write(code)
print("Mac crash patched.")
