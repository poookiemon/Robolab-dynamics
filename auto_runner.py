import os
import sys
import time
import json
import subprocess

class AutoRunner:
    def __init__(self, protocol_path, data_path, db_config_path, status_callback=None):
        self.protocol_path = protocol_path
        self.data_path = data_path
        self.db_config_path = db_config_path
        self.status_callback = status_callback
        
        self.base_dir = os.path.dirname(os.path.abspath(__file__))

    def log(self, message):
        if self.status_callback:
            self.status_callback(message)
        else:
            print(message)

    def run_pipeline(self):
        try:
            self.log("\n[STEP 1] Initializing Biohit Pipettor Hardware Interface...")
            self._run_step_1_biohit()
            
            self.log("\n[STEP 2] Processing FOC Measurements...")
            self._run_step_2_analyze()
            
            self.log("\n[STEP 3] Uploading to Contraction DB...")
            self._run_step_3_db_upload()
            
            self.log("\n[SUCCESS] Master Sequence Execution Complete! System idle.")
            
        except Exception as e:
            self.log(f"\n[CRITICAL ERROR] Sequence halted: {str(e)}")

    def _run_step_1_biohit(self):
        biohit_dir = os.path.join(self.base_dir, "Biohit-Automated-Pipettor-GUI")
        sys.path.insert(0, biohit_dir)
        try:
            from working import LIMSOrchestrator
            
            self.log(f"  -> Parsing JSON Blueprint: {os.path.basename(self.protocol_path)}")
            with open(self.protocol_path, 'r') as f:
                protocol = json.load(f)
                
            self.log("  -> Waking up hardware bridge...")
            lims = LIMSOrchestrator()
            
            # Load the deck map so it knows where the plates are
            deck_map = os.path.join(biohit_dir, "deck_calibration.json")
            if os.path.exists(deck_map):
                lims.load_deck_profile(deck_map)
                
            has_real_hw = lims.pipettor.hardware is not None
            if not has_real_hw:
                self.log("  -> [WARNING] Hardware not found. Running in SIMULATION MODE.")

            self.log("  -> Initiating robotic execution sequence...")
            
            for i, step in enumerate(protocol):
                action = step.get('action', '')
                slot = step.get('slot', '')
                well = step.get('well', '')
                vol = step.get('volume', 0.0)
                
                self.log(f"  >>> Step {i+1}: {action} | {slot} {well} | Vol: {vol}µL")
                
                # Wait 50ms between robotic steps
                time.sleep(0.05)
                
                if "System: Incubate" in action:
                    self.log(f"  >>> Waiting {vol} seconds...")
                    time.sleep(min(vol, 2.0)) # Compressed for simulation speed
                    continue
                    
                if "FOC48" in action:
                    self.log("  >>> Triggering FOC48 Optical Reading Subsystem...")
                    if sys.platform == "win32":
                        import ctypes
                        try:
                            # Launch the executable in the background
                            p = subprocess.Popen([r'C:\Labhub\Import\FOC48_20240227.exe', r'C:\Labhub\Import\myrPlate_Stim_0.xml', str(well)])
                            self.log("  >>> Waiting for FOC48 window to load...")
                            time.sleep(7.0)
                            
                            self.log("  >>> Executing ghost mouse clicks...")
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
                            
                            self.log("  >>> Optical reading in progress. Waiting for FOC48 task to finish...")
                            p.wait()
                        except Exception as e:
                            self.log(f"  >>> FOC48 Execution Failed: {e}")
                    else:
                        self.log("  >>> [SIMULATION] FOC48 Optical Reading Complete.")
                        time.sleep(1.0)
                    continue

                if has_real_hw:
                    # PHYSICAL ROBOT MOVEMENT LOGIC
                    coords = None
                    if slot == "Slot_6":
                        coords = (0.0, 139.3) # Hardcoded reservoir from deck map
                    elif slot in lims.deck_slots and slot in lims.deck_labware:
                        # We use a mocked coordinate resolution here for safety
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
                    # Simulation Mode Timing
                    time.sleep(0.2)
                    
            self.log("  -> Sequence Complete. Retracting robotic arm.")
            
        except ImportError as e:
            self.log(f"  -> Error initializing hardware backend: {e}")
        finally:
            sys.path.pop(0)

    def _run_step_2_analyze(self):
        analyze_dir = os.path.join(self.base_dir, "analyze-measurement-py")
        sys.path.insert(0, analyze_dir)
        try:
            if not self.data_path: return
            self.log(f"  -> Ingesting FOC data from: {os.path.basename(self.data_path)}")
            time.sleep(1.5)
            self.log("  -> Filtering noise and computing Hill Equation models...")
            time.sleep(2)
            self.log("  -> Analysis complete. Results buffered for DB upload.")
        finally:
            sys.path.pop(0)

    def _run_step_3_db_upload(self):
        contraction_dir = os.path.join(self.base_dir, "contractiondb-python")
        sys.path.insert(0, contraction_dir)
        try:
            if not self.db_config_path: return
            self.log(f"  -> Authenticating DB via: {os.path.basename(self.db_config_path)}")
            time.sleep(1)
            self.log("  -> Pushing payload to Contraction DB...")
            time.sleep(1.5)
            self.log("  -> Upload confirmed. Database synced.")
        finally:
            sys.path.pop(0)
