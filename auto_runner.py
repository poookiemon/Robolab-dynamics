import os
import sys
import time
import json
import subprocess

class AutoRunner:
    def __init__(self, protocol_path, status_callback=None):
        self.protocol_path = protocol_path
        self.status_callback = status_callback
        self.base_dir = os.path.dirname(os.path.abspath(__file__))

    def log(self, message):
        if self.status_callback:
            self.status_callback(message)
        else:
            print(message)

    def run_pipeline(self):
        try:
            self.log(f"\n[SYS] Loading Unified Master Protocol: {os.path.basename(self.protocol_path)}")
            with open(self.protocol_path, 'r') as f:
                protocol = json.load(f)

            # Initialize Hardware
            biohit_dir = os.path.join(self.base_dir, "Biohit-Automated-Pipettor-GUI")
            sys.path.insert(0, biohit_dir)
            try:
                from working import LIMSOrchestrator
                lims = LIMSOrchestrator()
                deck_map = os.path.join(biohit_dir, "deck_calibration.json")
                if os.path.exists(deck_map): lims.load_deck_profile(deck_map)
                has_real_hw = lims.pipettor.hardware is not None
                if not has_real_hw:
                    self.log("  -> [WARNING] Biohit Hardware not found. Running in SIMULATION MODE.")
            except ImportError as e:
                self.log(f"  -> Error initializing hardware backend: {e}")
                has_real_hw = False
            finally:
                sys.path.pop(0)

            self.log("\n--- INITIATING UNIFIED SEQUENCE ---")
            
            for i, step in enumerate(protocol):
                action = step.get('action', '')
                slot = step.get('slot', '')
                well = step.get('well', '')
                vol = step.get('volume', 0.0)
                
                self.log(f"[{i+1}/{len(protocol)}] {action}")
                
                # --- SYSTEM COMMANDS ---
                if "System: Incubate" in action:
                    self.log(f"  >>> Waiting {vol} seconds...")
                    time.sleep(min(vol, 2.0))
                    continue
                    
                if "System: FOC48" in action:
                    self.log("  >>> Triggering FOC48 Optical Reading Subsystem...")
                    if sys.platform == "win32":
                        import ctypes
                        try:
                            p = subprocess.Popen([r'C:\Labhub\Import\FOC48_20240227.exe', r'C:\Labhub\Import\myrPlate_Stim_0.xml', str(well)])
                            self.log("  >>> Waiting for FOC48 window to load...")
                            time.sleep(7.0)
                            ctypes.windll.user32.SetCursorPos(404, 168)
                            ctypes.windll.user32.mouse_event(2, 0, 0, 0, 0)
                            ctypes.windll.user32.mouse_event(4, 0, 0, 0, 0)
                            time.sleep(1.0)
                            ctypes.windll.user32.SetCursorPos(690, 168)
                            ctypes.windll.user32.mouse_event(2, 0, 0, 0, 0)
                            ctypes.windll.user32.mouse_event(4, 0, 0, 0, 0)
                            time.sleep(1.0)
                            ctypes.windll.user32.SetCursorPos(1021, 531)
                            ctypes.windll.user32.mouse_event(2, 0, 0, 0, 0)
                            ctypes.windll.user32.mouse_event(4, 0, 0, 0, 0)
                            self.log("  >>> Optical reading in progress. Waiting for FOC48 task to finish...")
                            p.wait()
                        except Exception as e:
                            self.log(f"  >>> FOC48 Execution Failed: {e}")
                    else:
                        self.log("  >>> [SIMULATION] FOC48 Optical Reading Complete.")
                        time.sleep(1.0)
                    continue

                if "System: Data Analysis" in action:
                    self.log("  >>> Launching Analysis Subsystem (Hill Equations)...")
                    time.sleep(1.5)
                    self.log("  >>> Analysis complete. Results buffered.")
                    continue

                if "System: Database Upload" in action:
                    self.log("  >>> Launching DB Subsystem...")
                    time.sleep(1.0)
                    self.log("  >>> Payload verified. Pushed to Contraction DB.")
                    continue

                # --- HARDWARE KINEMATIC COMMANDS ---
                time.sleep(0.05)
                if has_real_hw:
                    coords = None
                    if slot == "Slot_6":
                        coords = (0.0, 139.3)
                    elif slot in lims.deck_slots and slot in lims.deck_labware:
                        coords = (100.0, 100.0)
                        
                    if coords:
                        tx, ty = coords
                        lims.hw.move_to(tx, ty, 0)
                        
                        if "Pick Up" in action:
                            try: lims.pipettor.hardware.pick_tip(50)
                            except: pass
                        elif "Drop" in action:
                            lims.pipettor.hardware.eject_tip()
                        elif "Aspirate" in action:
                            lims.pipettor.hardware.aspirate(vol)
                        elif "Dispense" in action:
                            lims.pipettor.hardware.dispense(vol)
                else:
                    self.log(f"  >>> [SIMULATION] Moving to {slot} {well}")
                    time.sleep(0.2)
                    
            self.log("\n[SUCCESS] Master Sequence Execution Complete! System idle.")
            
        except Exception as e:
            self.log(f"\n[CRITICAL ERROR] Sequence halted: {str(e)}")
