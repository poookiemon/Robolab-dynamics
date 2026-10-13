import sys
import os
import json
import time
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

import traceback
try:
    from biohit_pipettor import Pipettor as RealBiohitPipettor
    HAS_BIOHIT_DLL = True
    print("SUCCESS: Hardware Bridge Established via native biohit_pipettor package.")
except Exception as e:
    HAS_BIOHIT_DLL = False
    print(f"CRITICAL: Bridge failed. Ensure 'biohit_pipettor' is installed. Error: {e}")
    traceback.print_exc()
    RealBiohitPipettor = None


@dataclass
class DeckSlot:
    name: str
    x_abs: float
    y_abs: float
    width_mm: float
    height_mm: float
    z_offset: float = 0.0


@dataclass
class Well:
    name: str
    x_rel: float
    y_rel: float
    radius: float
    depth_mm: float = 0.0


class Labware:
    def __init__(self, filepath: str):
        if not os.path.exists(filepath):
            self.name = "Mock_Labware"
            self.columns = 12
            self.rows = 8
            self.z_height_mm = 20.0
            self.wells = {"A1": Well("A1", 0, 0, 3, 18.0)}
            return

        with open(filepath, 'r') as f:
            data = json.load(f)
        self.name = data.get('labware_name', "Unknown")
        grid = data.get('grid', {"rows": 8, "columns": 12})
        self.columns = grid.get('columns', 12)
        self.rows = grid.get('rows', 8)

        self.z_height_mm = data.get('z_height_mm', 20.0)
        self.wells: Dict[str, Well] = self._generate_wells(data)

        # --- NEW: Inject Explicit JSON UI Coordinates ---
        if 'wells' in data:
            for w_id, w_coords in data['wells'].items():
                if w_id in self.wells:
                    self.wells[w_id].x_rel = w_coords.get('x_rel', 0.0)
                    self.wells[w_id].y_rel = w_coords.get('y_rel', 0.0)
        # ------------------------------------------------

        # --- Hardcoded Parameter Intercept for Known Labware ---
        file_lower = filepath.lower()
        if "reservoir" in file_lower:
            self.z_height_mm = 105.81
            for w in self.wells.values(): w.depth_mm = 54.0 * 0.75
        elif "waste" in file_lower:
            self.z_height_mm = 43.35
            for w in self.wells.values(): w.depth_mm = 43.35
        elif "corning" in file_lower or "ehm" in file_lower:
            self.z_height_mm = 78.42
            for w in self.wells.values(): w.depth_mm = 16.90
        elif "tip" in file_lower:
            self.z_height_mm = 78.18
            for w in self.wells.values(): w.depth_mm = 9.65

    def _generate_wells(self, data) -> Dict[str, Well]:
        wells = {}
        offset = data.get('well_a1_offset', {"x": 0, "y": 0})
        start_x, start_y = offset.get('x', 0), offset.get('y', 0)

        spacing = data.get('spacing', {"x": 9, "y": 9})
        pitch_x, pitch_y = spacing.get('x', 9), spacing.get('y', 9)

        well_props = data.get('well_properties', {})
        radius = well_props.get('radius_mm', 3.0)
        depth = well_props.get('depth_mm', self.z_height_mm - 2.0)

        for r in range(self.rows):
            row_label = chr(65 + r)
            for c in range(self.columns):
                well_id = f"{row_label}{c + 1}"
                wells[well_id] = Well(well_id, start_x + (c * pitch_x), start_y + (r * pitch_y), radius, depth)
        return wells


class Pipettor:
    def __init__(self, tip_volume: float = 200.0, multichannel: bool = False):
        self.tip_volume = tip_volume
        self.multichannel = multichannel
        self.channels = 8 if multichannel else 1
        self.hardware_context = None
        self.hardware = None

        if HAS_BIOHIT_DLL:
            try:
                # Biohit hardware driver strictly accepts 200 or 1000 uL (PipetType: 1=200uL, 2=1000uL)
                vol_literal = 200
                self.hardware_context = RealBiohitPipettor(
                    tip_volume=vol_literal,
                    multichannel=multichannel,
                    initialize=False
                )
                self.hardware = self.hardware_context.__enter__()
            except Exception as e:
                print(f"Hardware Initialization Error: {e}")

    def close(self):
        if self.hardware_context:
            try:
                self.hardware_context.__exit__(None, None, None)
            except Exception as e:
                print(f"Error closing pipettor: {e}")
            finally:
                self.hardware_context = None
                self.hardware = None

    def __del__(self):
        self.close()


class BiohitInterface:
    def __init__(self, pipettor: Pipettor = None, limits: dict = None):
        self.is_initialized = False
        self.pipettor = pipettor if pipettor else Pipettor()
        self.limits = limits if limits else {"max_x_mm": 300.0, "max_y_mm": 300.0, "max_z_mm": 310.0}

    def scan_ports(self) -> List[str]:
        return ["NATIVE_PACKAGE_BRIDGE"] if HAS_BIOHIT_DLL else ["MOCK_PORT"]

    def connect(self, port_name: str) -> Tuple[bool, str]:
        if self.pipettor.hardware:
            return True, "Connected via native biohit module."
        elif not HAS_BIOHIT_DLL:
            return True, "Connected in Simulation Mode."
        return False, "Connection rejected."

    def initialize(self) -> Tuple[bool, str]:
        if self.pipettor.hardware:
            try:
                self.pipettor.hardware.initialize()
                self.is_initialized = True
                return True, "Homed & Initialized via DLL."
            except Exception as e:
                return False, f"Initialization failed: {str(e)}"
        else:
            self.is_initialized = True
            return True, "Homed & Initialized (Simulation)."

    def smart_tip_pickup(self, slot_name, labware_obj, logger):
        try:
            if self.pipettor.hardware:
                self.pipettor.hardware.tip_pickup_force = 22
                self.pipettor.hardware.pick_tip(75)
            return True, True
        except Exception as e:
            if logger: logger.warning(f"Tip pick error: {e}")
            return False, False

    def move_to(self, x: float, y: float, z: float, speed: int = 50, clearance: bool = True):
        safe_x = max(0.0, min(x, self.limits.get("max_x_mm", 300.0)))
        safe_y = max(0.0, min(y, self.limits.get("max_y_mm", 300.0)))
        safe_z = max(0.0, z)

        if self.is_initialized and self.pipettor.hardware:
            hw_speed = max(1, min(9, int((speed / 100.0) * 9)))
            try:
                self.pipettor.hardware.x_speed = hw_speed
                self.pipettor.hardware.y_speed = hw_speed
                self.pipettor.hardware.z_speed = hw_speed
                self.pipettor.hardware.tip_pickup_force = 20

                self.pipettor.hardware.aspirate_speed = 1
                try:
                    self.pipettor.hardware.dispense_speed = 5
                except AttributeError:
                    pass
            except Exception as e:
                print(f"Speed attribute error: {e}")

            try:
                if clearance: self.pipettor.hardware.move_z(0, wait=True)
                try:
                    self.pipettor.hardware.move_xy(safe_x, safe_y, speed=hw_speed, wait=True)
                except TypeError:
                    self.pipettor.hardware.move_xy(safe_x, safe_y, wait=True)
                if z > 0: self.pipettor.hardware.move_z(safe_z, wait=True)
            except Exception as e:
                print(f"Move error: {e}")


class LIMSOrchestrator:
    def __init__(self, hardware: Pipettor = None):
        self.deck_slots: Dict[str, DeckSlot] = {}
        self.deck_labware: Dict[str, Labware] = {}
        self.pipettor = hardware if hardware else Pipettor()
        self.machine_config = {}
        self.load_machine_profile()
        self.hw = BiohitInterface(pipettor=self.pipettor, limits=self.machine_config)

    def load_machine_profile(self, filepath: str = "machine_profile.json"):
        if not os.path.exists(filepath):
            self.machine_config = {"brand": "Biohit", "max_x_mm": 300.0, "max_y_mm": 300.0, "max_z_mm": 310.0,
                                   "tip_length_mm": 50.89}
            self.save_machine_profile(filepath)
            return
        with open(filepath, 'r') as f:
            self.machine_config = json.load(f)
        if "tip_length_mm" not in self.machine_config: self.machine_config["tip_length_mm"] = 50.89
        self.machine_config["max_z_mm"] = 310.0

    def save_machine_profile(self, filepath: str = "machine_profile.json"):
        with open(filepath, 'w') as f: json.dump(self.machine_config, f, indent=4)

    def load_deck_profile(self, filepath: str):
        if not os.path.exists(filepath): raise FileNotFoundError(f"Missing {filepath}.")
        with open(filepath, 'r') as f:
            data = json.load(f)
        self.deck_slots.clear()
        for s in data.values():
            self.deck_slots[s['name']] = DeckSlot(s['name'], s['x_abs'], s['y_abs'], s['width_mm'], s['height_mm'],
                                                  s.get('z_offset', 0.0))

    def save_deck_profile(self, filepath: str = "deck_calibration.json"):
        data = {
            n: {"name": s.name, "x_abs": s.x_abs, "y_abs": s.y_abs, "width_mm": s.width_mm, "height_mm": s.height_mm,
                "z_offset": s.z_offset} for n, s in self.deck_slots.items()}
        with open(filepath, 'w') as f: json.dump(data, f, indent=4)

    def update_slot_dimensions_from_ui(self, slot_name: str, **kwargs):
        if slot_name in self.deck_slots:
            s = self.deck_slots[slot_name]
            if "x_abs" in kwargs: s.x_abs = kwargs["x_abs"]
            if "y_abs" in kwargs: s.y_abs = kwargs["y_abs"]
            if "width" in kwargs: s.width_mm = kwargs["width"]
            if "height" in kwargs: s.height_mm = kwargs["height"]
            if "z_offset" in kwargs: s.z_offset = kwargs["z_offset"]

    def load_liquid_classes(self, filepath: str):
        pass

    def assign_labware_to_slot(self, slot_name: str, labware: Labware):
        self.deck_labware[slot_name] = labware

    def get_target_xy(self, slot_name: str, well_id: str):
        if slot_name not in self.deck_slots:
            raise ValueError(f"Slot {slot_name} missing")

        slot = self.deck_slots[slot_name]
        sy = slot.y_abs

        # --- ABSOLUTE OVERRIDE FOR SLOT 3 TIP RACK ---
        if slot_name == "Slot_3":
            col_x = {
                '1': 242.0, '2': 233.0, '3': 224.0, '4': 215.0,
                '5': 206.0, '6': 197.0, '7': 188.0, '8': 179.0,
                '9': 170.0, '10': 161.0, '11': 152.0, '12': 143.0
            }
            row_y = {
                'A': 60.0,  'B': 69.0,  'C': 78.0,  'D': 87.0,
                'E': 96.0,  'F': 105.0, 'G': 114.0, 'H': 123.0
            }
            if len(well_id) >= 2:
                r_c = well_id[0].upper()
                c_c = well_id[1:]
                if r_c in row_y and c_c in col_x:
                    return col_x[c_c], row_y[r_c]

            if hasattr(self, 'logger'):
                self.logger.warning(f"Slot 3 Override: Well {well_id} falls outside defined 96-tip grid.")

        # --- ABSOLUTE OVERRIDE FOR SLOT 4 EHM PLATE ---
        if slot_name == "Slot_4":
            col_x = {'1': 105.00, '2': 87.00, '3': 68.88, '4': 51.54, '5': 34.20, '6': 15.60}
            row_y = {
                'A': 67.30, 'B': 75.30, 'C': 85.30, 'D': 95.30,
                'E': 105.30, 'F': 113.30, 'G': 121.30, 'H': 129.30
            }
            if len(well_id) >= 2:
                r_c = well_id[0].upper()
                c_c = well_id[1:]
                if r_c in row_y and c_c in col_x:
                    return col_x[c_c], row_y[r_c]

            if hasattr(self, 'logger'):
                self.logger.warning(f"Slot 4 Override: Well {well_id} falls outside defined EHM grid.")

        # --- ABSOLUTE OVERRIDE FOR SLOT 5 REAGENT RESERVOIR ---
        if slot_name == "Slot_5":
            col_x = {
                '1': 239.0, '2': 220.0, '3': 201.0,
                '4': 182.0, '5': 163.0, '6': 144.0
            }
            col_char = well_id[1:] if len(well_id) >= 2 else '1'
            target_x = col_x.get(col_char, 191.5)
            target_y = 207.75
            return target_x, target_y

        cx = slot.x_abs + (slot.width_mm / 2.0)
        cy = slot.y_abs + (slot.height_mm / 2.0)

        # Force dead-center geometric tracking for waste trough ONLY
        if slot_name == "Slot_6":
            return cx, cy

        if slot_name not in self.deck_labware:
            raise ValueError(f"Labware missing at {slot_name}")

        labware = self.deck_labware[slot_name]

        if well_id not in labware.wells:
            raise ValueError(f"Well {well_id} missing.")

        first_w = list(labware.wells.values())[0]
        lw_w = max(w.x_rel for w in labware.wells.values()) + first_w.x_rel
        lw_h = max(w.y_rel for w in labware.wells.values()) + first_w.y_rel
        well_obj = labware.wells[well_id]

        target_x = cx + ((lw_w / 2.0) - well_obj.x_rel)

        if self.pipettor.multichannel:
            col_str = well_id[1:]
            row_char_first = 'A'
            row_char_last = chr(ord('A') + labware.rows - 1)

            w_first = labware.wells.get(f"{row_char_first}{col_str}", well_obj)
            w_last = labware.wells.get(f"{row_char_last}{col_str}", well_obj)

            target_y_first = slot.y_abs + w_first.y_rel
            target_y_last = slot.y_abs + w_last.y_rel
            target_y = (target_y_first + target_y_last) / 2.0
        else:
            target_y = cy - (lw_h / 2.0) + well_obj.y_rel

        return target_x, target_y

    def get_target_z(self, action: str, slot_name: str, well_id: str, has_tips: bool = True,
                     extra_z: float = 0.0) -> float:
        if action == "Pick Up Tip":
            return 0.0

        slot_obj = self.deck_slots.get(slot_name)
        slot_z_offset = slot_obj.z_offset if slot_obj else 0.0
        labware_obj = self.deck_labware.get(slot_name)

        if action in ["Aspirate Media", "Dispense Media", "Discard Tip"]:
            # --- Z-DEPTH FIX: Force 102.0mm for EHM plates to prevent air-drawing ---
            if slot_name == "Slot_4" or (labware_obj and "ehm" in labware_obj.name.lower()):
                base_z = 98.0
            elif slot_name == "Slot_5":
                base_z = 105.0
            elif slot_name == "Slot_6":
                base_z = 90.0
            elif action == "Discard Tip" and slot_name == "Slot_1":
                base_z = 90.0
            elif labware_obj and (
                    getattr(labware_obj, 'z_height_mm', 20.0) == 105.81 or "reservoir" in labware_obj.name.lower()):
                base_z = 105.0
            else:
                base_z = 101.0

            return base_z + slot_z_offset + extra_z

        return 0.0

    def execute_transfer(self, source_slot: str, source_well: str, dest_slot: str, dest_well: str, volume: float,
                         liquid_class_name: str = ""):
        try:
            src_x, src_y = self.get_target_xy(source_slot, source_well)
            dest_x, dest_y = self.get_target_xy(dest_slot, dest_well)

            src_z = self.get_target_z("Aspirate Media", source_slot, source_well, has_tips=True)
            dest_z = self.get_target_z("Dispense Media", dest_slot, dest_well, has_tips=True)
        except Exception as e:
            print(f"Coordinate Error: {e}")
            return

        transfer_type = "8-Channel" if self.pipettor.multichannel else "Single-Channel"
        max_vol = self.pipettor.tip_volume
        remaining_vol = float(volume)

        print(f"[{transfer_type}] Initiating automated transfer of {volume}uL (Tip Capacity: {max_vol}uL)")

        # --- AUTOMATED VOLUME SLICING LOOP ---
        while remaining_vol > 0:
            chunk = min(remaining_vol, max_vol)
            print(f" -> Cycle: Transferring chunk of {chunk:.1f}uL. Remaining: {remaining_vol - chunk:.1f}uL")

            # Aspirate Chunk
            self.hw.move_to(src_x, src_y, src_z)
            if self.pipettor.hardware:
                try:
                    self.pipettor.hardware.aspirate(chunk)
                    time.sleep(1.5)  # Hydrostatic equilibration pause
                except Exception as e:
                    print(f"Aspirate failed: {e}")

            # Dispense Chunk
            self.hw.move_to(dest_x, dest_y, dest_z)
            if self.pipettor.hardware:
                try:
                    self.pipettor.hardware.dispense(chunk)
                    time.sleep(0.05)
                    self.pipettor.hardware.dispense(50)  # Droplet blowout
                except Exception as e:
                    print(f"Dispense failed: {e}")

            remaining_vol -= chunk

        if self.pipettor.hardware:
            try:
                self.pipettor.hardware.move_z(0)
            except TypeError:
                self.pipettor.hardware.move_z(0)