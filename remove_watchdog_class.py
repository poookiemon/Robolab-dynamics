import re

with open('Biohit-Automated-Pipettor-GUI/lims_pyqt.py', 'r') as f:
    code = f.read()

start = code.find("class WatchdogRunner(QThread):")
if start != -1:
    end = code.find("class LIMSPyQtApp(QMainWindow):", start)
    if end != -1:
        code = code[:start] + code[end:]
        with open('Biohit-Automated-Pipettor-GUI/lims_pyqt.py', 'w') as f:
            f.write(code)
        print("REMOVED WATCHDOG CLASS")
