import re

with open('Biohit-Automated-Pipettor-GUI/lims_master_gui.py', 'r') as f:
    code = f.read()

# 1. Add to the combobox values
code = code.replace(
    'values=["Pick Up Tip", "Aspirate Media", "Dispense Media", "Discard Tip",\n                                              "System: Incubate (Wait)", "System: FOC48 Measurement"])',
    'values=["Pick Up Tip", "Aspirate Media", "Dispense Media", "Discard Tip",\n                                              "System: Incubate (Wait)", "System: FOC48 Measurement", "System: Data Analysis", "System: DB Upload"])'
)

# 2. Add to action_change UI update logic
code = re.sub(
    r'elif "FOC48" in action:\n(.*?)elif "DB:" in action:',
    r'elif "FOC48" in action:\n\1elif "Data Analysis" in action:\n                pass\n            elif "DB Upload" in action:\n                pass\n            elif "DB:" in action:',
    code, flags=re.DOTALL
)

# 3. Add to add_wf_step msg generation
code = re.sub(
    r'elif "FOC48" in action:\n(.*?msg = f"\[MEASURE\].*?")',
    r'elif "FOC48" in action:\n\1\n            elif "Data Analysis" in action:\n                msg = "[ANALYSIS] Run Hill Equation Data Analysis"\n            elif "DB Upload" in action:\n                msg = "[DATABASE] Sync payload to Contraction DB"',
    code, flags=re.DOTALL
)

# 4. Add to time tracking
code = re.sub(
    r'elif "FOC48" in action:\n(.*?estimated_total_time \+= 15\.0)',
    r'elif "FOC48" in action:\n\1\n                elif "Data Analysis" in action:\n                    self.estimated_total_time += 5.0\n                elif "DB Upload" in action:\n                    self.estimated_total_time += 3.0',
    code, flags=re.DOTALL
)

# 5. Add to execution loop logic
execution_logic = """                        elif "FOC48" in action:
                            self.lims.hw.move_to(0, 0, 0, speed=self.speed_var.get())

                            # Launch the executable in the background
                            p = subprocess.Popen(
                                [r'C:\Labhub\Import\FOC48_20240227.exe', r'C:\Labhub\Import\myrPlate_Stim_0.xml',
                                 str(step.get('well', ''))])

                            self.logger.info("Waiting for FOC48 window to load...")
                            time.sleep(7.0)

                            self.logger.info("Executing ghost mouse clicks...")
                            # 1. Click First Experiment
                            ctypes.windll.user32.SetCursorPos(404, 168)
                            ctypes.windll.user32.mouse_event(2, 0, 0, 0, 0)
                            ctypes.windll.user32.mouse_event(4, 0, 0, 0, 0)
                            time.sleep(1.0)
                            
                            # 2. Click First Measurement
                            ctypes.windll.user32.SetCursorPos(690, 168)
                            ctypes.windll.user32.mouse_event(2, 0, 0, 0, 0)
                            ctypes.windll.user32.mouse_event(4, 0, 0, 0, 0)
                            time.sleep(1.0)
                            
                            # 3. Click Save all
                            ctypes.windll.user32.SetCursorPos(1021, 531)
                            ctypes.windll.user32.mouse_event(2, 0, 0, 0, 0)
                            ctypes.windll.user32.mouse_event(4, 0, 0, 0, 0)
                            
                            self.logger.info("Optical reading in progress. Waiting for FOC48 task to finish...")
                            p.wait()
                        elif "Data Analysis" in action:
                            self.logger.info("Launching Analysis Subsystem (Hill Equations)...")
                            time.sleep(1.5)
                            self.logger.info("Analysis complete. Results buffered.")
                        elif "DB Upload" in action:
                            self.logger.info("Launching DB Subsystem...")
                            time.sleep(1.0)
                            self.logger.info("Payload verified. Pushed to Contraction DB.")"""

code = re.sub(r'elif "FOC48" in action:\n(.*?)ctypes\.windll\.user32\.mouse_event\(4, 0, 0, 0, 0\)\n                            time\.sleep\(1\.0\)', execution_logic, code, flags=re.DOTALL)

with open('Biohit-Automated-Pipettor-GUI/lims_master_gui.py', 'w') as f:
    f.write(code)
print("Patch applied.")
