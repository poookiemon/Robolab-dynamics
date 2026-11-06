with open('Biohit-Automated-Pipettor-GUI/lims_pyqt.py', 'r') as f:
    lines = f.readlines()

new_lines = []
in_watchdog = False
watchdog_class_lines = []

for line in lines:
    if line.startswith("class WatchdogRunner(QThread):"):
        in_watchdog = True
        watchdog_class_lines.append(line)
        continue
        
    if in_watchdog:
        if line.startswith("    def build_analysis_tab(self):"):
            in_watchdog = False
            new_lines.append(line)
        else:
            watchdog_class_lines.append(line)
    else:
        new_lines.append(line)

# Insert the WatchdogRunner class at the top, just before LIMSPyQtApp
# LIMSPyQtApp starts at: class LIMSPyQtApp(QMainWindow):
insert_idx = 0
for i, line in enumerate(new_lines):
    if line.startswith("class LIMSPyQtApp(QMainWindow):"):
        insert_idx = i
        break

final_lines = new_lines[:insert_idx] + watchdog_class_lines + ["\\n"] + new_lines[insert_idx:]

with open('Biohit-Automated-Pipettor-GUI/lims_pyqt.py', 'w') as f:
    f.writelines(final_lines)

print("FILE REWRITTEN")
