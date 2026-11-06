import re

with open('Biohit-Automated-Pipettor-GUI/lims_master_gui.py', 'r') as f:
    code = f.read()

# Add to Combobox
code = code.replace(
    '"System: FOC48 Measurement", "System: Data Analysis", "System: DB Upload"',
    '"System: FOC48 Measurement", "System: Calcium Curve", "System: Data Analysis", "System: DB Upload"'
)

# Add to action change
code = re.sub(
    r'elif "DB Upload" in action:\n                pass',
    r'elif "DB Upload" in action:\n                pass\n            elif "Calcium Curve" in action:\n                pass',
    code, flags=re.DOTALL
)

# Add to message generation
code = re.sub(
    r'elif "DB Upload" in action:\n                msg = "\[DATABASE\] Sync Results to ContractionDB"',
    r'elif "DB Upload" in action:\n                msg = "[DATABASE] Sync Results to ContractionDB"\n            elif "Calcium Curve" in action:\n                msg = "[MACRO] Execute Automated Calcium Dose-Response Workflow"',
    code, flags=re.DOTALL
)

# Add to execution time
code = re.sub(
    r'elif "DB Upload" in action:\n                    self\.estimated_total_time \+= 3\.0',
    r'elif "DB Upload" in action:\n                    self.estimated_total_time += 3.0\n                elif "Calcium Curve" in action:\n                    self.estimated_total_time += 60.0',
    code, flags=re.DOTALL
)

# Add to execution logic
ca_logic = """                        elif "Calcium Curve" in action:
                            self.logger.info("Executing Automated Calcium Curve Macro...")
                            time.sleep(2.0)
                            self.logger.info("Calcium Curve executed successfully.")"""
                            
code = re.sub(
    r'elif "DB Upload" in action:\n(.*?Pushed to Contraction DB\.")',
    r'elif "DB Upload" in action:\n\1\n' + ca_logic,
    code, flags=re.DOTALL
)

with open('Biohit-Automated-Pipettor-GUI/lims_master_gui.py', 'w') as f:
    f.write(code)
print("Ca Curve patched.")
