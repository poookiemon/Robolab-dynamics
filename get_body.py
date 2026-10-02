import re
with open('Biohit-Automated-Pipettor-GUI/lims_pyqt.py', 'r') as f:
    code = f.read()

start = code.find("def draw_deck(self):")
if start != -1:
    end = code.find("def _deck_jog(self):", start)
    print(code[start:end])
