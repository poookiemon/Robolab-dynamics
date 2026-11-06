import re

with open('/Users/shri/Robolab-dynamics/Biohit-Automated-Pipettor-GUI/lims_pyqt.py', 'r') as f:
    code = f.read()

# Replace the text3D block
bad_text_block = """                try:
                    text = pv.Text3D(name.replace('_', ' '), depth=1.0)
                    text.scale((4, 4, 4), inplace=True)
                    text.translate((slot.x_abs + 10, slot.y_abs + 10, 7.0), inplace=True)
                    self.plotter.add_mesh(text, color="white")
                except: pass"""

safe_text = """                # Use safe 2D point labels instead of Text3D which corrupts macOS VTK bounds
                self.plotter.add_point_labels(
                    [(slot.x_abs + slot.width_mm/2, slot.y_abs + slot.height_mm/2, 8.0)],
                    [name.replace('_', ' ')],
                    text_color='white',
                    point_color='white',
                    point_size=1,
                    font_size=18,
                    shape=None,
                    show_points=False
                )"""

code = code.replace(bad_text_block, safe_text)

with open('/Users/shri/Robolab-dynamics/Biohit-Automated-Pipettor-GUI/lims_pyqt.py', 'w') as f:
    f.write(code)

print("Nuked Text3D")
