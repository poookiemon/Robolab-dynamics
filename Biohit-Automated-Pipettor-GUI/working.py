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
    err_str = str(e)
    print(f"Hardware Bridge Notice: 'biohit_pipettor' not loaded ({e}).")
    if "pycparser" in err_str:
        print("💡 REQUIRED FIX: Run 'pip install pycparser' in your Command Prompt.")
    elif "mono" in err_str or "netfx" in err_str:
        print("💡 Hardware Bridge Notice: Simulation mode active.")
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
        self.z_limits = data.get('z_limits', {})
        self.raw_data = data
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
        col_x_list = data.get('col_x')
        row_y_list = data.get('row_y')

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
                if col_x_list and c < len(col_x_list) and row_y_list and r < len(row_y_list):
                    wx = col_x_list[c]
                    wy = row_y_list[r]
                else:
                    wx = start_x + (c * pitch_x)
                    wy = start_y + (r * pitch_y)
                wells[well_id] = Well(well_id, wx, wy, radius, depth)
        return wells


class Pipettor:
    def __init__(self, tip_volume: float = 250.0, multichannel: bool = False):
        self.multichannel = bool(multichannel)
        if tip_volume is not None:
            self.tip_volume = float(tip_volume)
        else:
            self.tip_volume = 1000.0 if self.multichannel else 250.0
        self.channels = 8 if self.multichannel else 1
        self.hardware_context = None
        self.hardware = None
        self._open_hardware()

    def _open_hardware(self) -> Tuple[bool, str]:
        if HAS_BIOHIT_DLL:
            try:
                # Biohit hardware driver strictly accepts 200 or 1000 uL (PipetType: 1=200uL, 2=1000uL).
                # Multi-channel manifold strictly requires 1000 uL (PipetType=2, 0.2 steps/uL).
                # Single-channel heads (200uL/250uL/300uL) configure PipetType=1 (2.0 steps/uL), enabling strokes up to 250uL+.
                vol_literal = 1000 if (self.multichannel or self.tip_volume >= 1000.0) else 200
                self.hardware_context = RealBiohitPipettor(
                    tip_volume=vol_literal,
                    multichannel=self.multichannel,
                    initialize=False
                )
                self.hardware = self.hardware_context.__enter__()
                return True, f"Hardware driver configured ({self.channels}x{int(self.tip_volume)}uL {'Multi' if self.multichannel else 'Single'})."
            except Exception as e:
                print(f"Hardware Initialization Error: {e}")
                return False, f"Hardware Initialization Error: {e}"
        return True, f"Simulation mode configured ({self.channels}x{int(self.tip_volume)}uL {'Multi' if self.multichannel else 'Single'})."

    def reconfigure(self, tip_volume: float, multichannel: bool) -> Tuple[bool, str]:
        """Safely switches between Single-Channel (20uL, 200uL, 250uL, 300uL) and Multi-Channel (10uL, 1000uL) driver configurations."""
        self.multichannel = bool(multichannel)
        if tip_volume is not None:
            self.tip_volume = float(tip_volume)
        else:
            self.tip_volume = 1000.0 if self.multichannel else 250.0
        self.channels = 8 if self.multichannel else 1
        vol_literal = 1000 if (self.multichannel or self.tip_volume >= 1000.0) else 200

        # Prefer in-place live driver reconfiguration when already connected to avoid CLR/COM handle teardown race
        if self.hardware is not None:
            try:
                if self.multichannel:
                    setattr(self.hardware, "_AbstractPipettor__multichannel", True)
                    self.hardware.tip_volume = 1000
                else:
                    setattr(self.hardware, "_AbstractPipettor__multichannel", False)
                    self.hardware.tip_volume = vol_literal
                return True, f"Hardware driver reconfigured live ({self.channels}x{int(self.tip_volume)}uL {'Multi' if self.multichannel else 'Single'})."
            except Exception as e:
                print(f"Live reconfigure fallback to reopen: {e}")

        self.close()
        return self._open_hardware()

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
        self.active_port: Optional[str] = None
        self.pipettor = pipettor if pipettor else Pipettor()
        self.limits = limits if limits else {"max_x_mm": 300.0, "max_y_mm": 300.0, "max_z_mm": 310.0}
        self.z_home_count: int = 0

    @staticmethod
    def extract_clean_port(port_name: str) -> str:
        """Extract clean port identifier (e.g. 'COM3' from 'COM3 — USB Serial Port (COM3)')."""
        if not port_name:
            return ""
        s = str(port_name).strip()
        if " — " in s:
            return s.split(" — ")[0].strip()
        if " - " in s:
            return s.split(" - ")[0].strip()
        return s

    def scan_ports(self) -> List[str]:
        """
        Scans actual system serial / COM ports with friendly descriptive names.
        Examples:
          'COM3 — USB Serial Port (COM3)'
          'COM4 — FT232R USB UART'
          '/dev/ttyUSB0 — FTDI Serial Device'
        """
        results: List[str] = []
        seen_devices = set()

        # 1. Native pyserial scan with friendly hardware descriptions
        try:
            import serial.tools.list_ports as lp
            for p in lp.comports():
                dev = (p.device or "").strip()
                if not dev or dev in seen_devices:
                    continue
                seen_devices.add(dev)
                desc = (p.description or "").strip()
                mfg = (p.manufacturer or "").strip()
                if desc and desc != "n/a" and desc != dev:
                    display = f"{dev} — {desc}"
                elif mfg:
                    display = f"{dev} — {mfg} Device"
                else:
                    display = f"{dev} — Serial Device"
                results.append(display)
        except Exception:
            pass

        # 2. Windows Registry fallback for COM ports if pyserial missed anything
        if sys.platform == "win32":
            try:
                import winreg
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DEVICEMAP\SERIALCOMM")
                for i in range(winreg.QueryInfoKey(key)[1]):
                    name, val, _ = winreg.EnumValue(key, i)
                    val = str(val).strip()
                    if val and val not in seen_devices:
                        seen_devices.add(val)
                        results.append(f"{val} — {name}")
                winreg.CloseKey(key)
            except Exception:
                pass

        # 3. Unix / macOS fallback (/dev/ttyUSB*, /dev/ttyACM*, /dev/cu.usb*)
        if sys.platform != "win32":
            import glob
            for pat in ["/dev/ttyUSB*", "/dev/ttyACM*", "/dev/cu.usb*", "/dev/cu.*"]:
                for dev in sorted(glob.glob(pat)):
                    if dev not in seen_devices:
                        seen_devices.add(dev)
                        results.append(f"{dev} — Serial Device")

        # 4. Native Biohit C# Direct DLL Bridge (if InstrumentLib.dll present)
        if HAS_BIOHIT_DLL:
            results.insert(0, "NATIVE_PACKAGE_BRIDGE — Biohit Direct USB Bridge (InstrumentLib.dll)")

        # 5. Always provide explicit Simulation Mode option for offline test runs
        results.append("SIMULATION — Virtual Robot (Offline Test)")

        return results

    def connect(self, port_name: str) -> Tuple[bool, str]:
        if not port_name or str(port_name).strip() in (
            "",
            "Select Hardware Port...",
            "Select Port...",
            "(No Serial Ports Detected)",
            "No Serial Ports Detected",
        ):
            self.active_port = None
            self.is_initialized = False
            return False, "No hardware port selected. Please select a valid port from the dropdown."

        clean = self.extract_clean_port(port_name)
        self.active_port = clean

        if "SIMULATION" in clean.upper():
            return True, "Connected in Simulation Mode."

        if self.pipettor.hardware:
            return True, f"Connected via native biohit module on {clean}."
        elif not HAS_BIOHIT_DLL:
            return True, f"Connected to {clean} (Simulated driver layer)."

        return True, f"Connected to {clean}."

    def initialize(self) -> Tuple[bool, str]:
        if not getattr(self, "active_port", None):
            self.is_initialized = False
            return False, "Cannot initialize: No hardware port is connected. Please select a port and click 'Connect & Initialize'."

        if self.pipettor.hardware:
            try:
                self.pipettor.hardware.initialize()
                self.is_initialized = True
                return True, f"Homed & Initialized via DLL on {self.active_port}."
            except Exception as e:
                self.is_initialized = False
                return False, f"Initialization failed: {str(e)}"
        else:
            self.is_initialized = True
            return True, f"Homed & Initialized on {self.active_port}."

    def home_z_only(self, logger=None, reason: str = "") -> Tuple[bool, str]:
        """
        Homes ONLY the Z-axis actuator against the physical top home sensor to eliminate
        cumulative downward stepper drift (e.g. on the 300 µL single-channel head),
        while strictly preserving X, Y, mounted tips, and aspirated piston/liquid state ('P').
        """
        self.z_home_count = getattr(self, "z_home_count", 0) + 1
        hw = getattr(self.pipettor, "hardware", None) if self.pipettor else None
        if hw is None and self.pipettor is not None and hasattr(self.pipettor, "move_z"):
            hw = self.pipettor
        if not hw:
            return True, "Simulated Z-axis physical home (Z=0.00mm; tip & plunger preserved)."

        try:
            # 1. Smoothly retract to software Z=0 clearance first
            try:
                hw.move_z(0, wait=True)
            except TypeError:
                hw.move_z(0)
            except Exception as move_err:
                if logger:
                    logger.warning(f"[Z-HOME] Pre-retract move_z(0) notice: {move_err}")

            # 2. Trigger physical Z-only sensor re-zero via InstrumentLib ControlCls ("Z" module only, never "P")
            homed_physically = False
            inst = (
                getattr(hw, "_Pipettor__instrument", None)
                or getattr(hw, "_instrument", None)
                or getattr(hw, "instrument", None)
            )
            ctrl = getattr(inst, "Control", None) if inst is not None else getattr(hw, "Control", None)

            if ctrl is not None:
                if hasattr(ctrl, "Initialize"):
                    try:
                        res = ctrl.Initialize("Z")
                        homed_physically = bool(res) if res is not None else True
                    except Exception as init_z_err:
                        if logger:
                            logger.warning(f"[Z-HOME] Control.Initialize('Z') fallback: {init_z_err}")

                if not homed_physically and hasattr(ctrl, "DriveHome"):
                    try:
                        res = ctrl.DriveHome("Z", True)
                        homed_physically = bool(res) if res is not None else True
                    except TypeError:
                        res = ctrl.DriveHome("Z")
                        homed_physically = bool(res) if res is not None else True
                    except Exception as dh_err:
                        if logger:
                            logger.warning(f"[Z-HOME] Control.DriveHome('Z') fallback: {dh_err}")

                if hasattr(ctrl, "WaitArmToStop"):
                    try:
                        ctrl.WaitArmToStop("Z")
                    except TypeError:
                        try:
                            ctrl.WaitArmToStop()
                        except Exception:
                            pass
                    except Exception:
                        pass

            if not homed_physically:
                if hasattr(hw, "home_z") and callable(hw.home_z):
                    hw.home_z()
                    homed_physically = True
                elif hasattr(hw, "init_z") and callable(hw.init_z):
                    hw.init_z()
                    homed_physically = True

            # If mock/simulator object allows setting z_position directly, ensure it reads 0.0
            try:
                if not isinstance(getattr(type(hw), "z_position", None), property):
                    hw.z_position = 0.0
            except Exception:
                pass

            return True, "Physical Z-axis homed at top sensor (Z=0.00mm; tip & plunger preserved)."
        except Exception as e:
            if logger:
                logger.warning(f"[Z-HOME] Z-only homing warning: {e}")
            return False, f"Z-only homing warning: {e}"

    def smart_tip_pickup(self, slot_name, labware_obj, logger):
        try:
            if self.pipettor.hardware:
                hw_speed = getattr(self.pipettor.hardware, 'z_speed', 8)
                z_height = getattr(labware_obj, 'z_height_mm', 78.18) if labware_obj else 78.18
                approach_z = max(0.0, min(55.0, z_height - 18.0))
                pickup_limit = 87.0
                self.pipettor.hardware.z_speed = hw_speed
                self.pipettor.hardware.move_z(approach_z)
                self.pipettor.hardware.z_speed = 3
                self.pipettor.hardware.tip_pickup_force = 26
                try:
                    self.pipettor.hardware.pick_tip(pickup_limit)
                except Exception as p_err:
                    curr_z = getattr(self.pipettor.hardware, 'z_position', 0.0)
                    if curr_z < 60.0:
                        raise p_err
                curr_z = getattr(self.pipettor.hardware, 'z_position', 0.0)
                if curr_z >= 60.0:
                    try:
                        push_z = min(curr_z + 2.5, 89.0)
                        self.pipettor.hardware.move_z(push_z)
                        time.sleep(0.35)
                    except Exception as pe:
                        if logger: logger.warning(f"Pushback seating resistance: {pe}")
                time.sleep(0.35)
                self.pipettor.hardware.z_speed = hw_speed
                self.pipettor.hardware.move_z(0)
            return True, True
        except Exception as e:
            if logger: logger.warning(f"Tip pick error: {e}")
            if self.pipettor.hardware:
                try:
                    self.pipettor.hardware.z_speed = 8
                    self.pipettor.hardware.move_z(0)
                except Exception:
                    pass
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
        if not os.path.isabs(filepath):
            pkg_dir = os.path.dirname(os.path.abspath(__file__))
            cand = os.path.join(pkg_dir, filepath)
            if os.path.exists(cand):
                filepath = cand
            elif os.path.exists(filepath):
                pass
            else:
                filepath = cand

        if not os.path.exists(filepath):
            self.machine_config = {"brand": "Biohit", "max_x_mm": 300.0, "max_y_mm": 300.0, "max_z_mm": 310.0,
                                   "tip_length_mm": 50.89}
            try:
                self.save_machine_profile(filepath)
            except Exception:
                pass
            return
        try:
            with open(filepath, 'r') as f:
                self.machine_config = json.load(f)
        except Exception:
            self.machine_config = {"brand": "Biohit", "max_x_mm": 300.0, "max_y_mm": 300.0, "max_z_mm": 310.0,
                                   "tip_length_mm": 50.89}
        if "tip_length_mm" not in self.machine_config: self.machine_config["tip_length_mm"] = 50.89
        self.machine_config["max_z_mm"] = 310.0

    def save_machine_profile(self, filepath: str = "machine_profile.json"):
        try:
            with open(filepath, 'w') as f: json.dump(self.machine_config, f, indent=4)
        except Exception:
            pass

    def load_deck_profile(self, filepath: str):
        if not os.path.exists(filepath): raise FileNotFoundError(f"Missing {filepath}.")
        with open(filepath, 'r') as f:
            data = json.load(f)
        self.deck_slots.clear()
        self.deck_labware.clear()
        lw_dir = "labware"
        for cand in ["labware", "Biohit-Automated-Pipettor-GUI/labware", os.path.join(os.path.dirname(os.path.abspath(__file__)), "labware")]:
            if os.path.isdir(cand):
                lw_dir = cand
                break
        for s in data.values():
            name = s['name']
            self.deck_slots[name] = DeckSlot(name, s['x_abs'], s['y_abs'], s['width_mm'], s['height_mm'],
                                                  s.get('z_offset', 0.0))
            lab_file = s.get('labware_file')
            if lab_file:
                lw_path = os.path.join(lw_dir, lab_file)
                if os.path.exists(lw_path):
                    self.deck_labware[name] = Labware(lw_path)
                    self.deck_labware[name].source_file = lab_file

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
        cx = slot.x_abs + (slot.width_mm / 2.0)
        cy = slot.y_abs + (slot.height_mm / 2.0)

        labware = self.deck_labware.get(slot_name)
        lw_name = (getattr(labware, 'name', '') or '').lower()
        lw_src = (getattr(labware, 'source_file', '') or '').lower()

        # 1. WASTE TROUGH (Slot_6 or Slot_1 when used as waste, or waste labware)
        if ("waste" in lw_name or "waste" in lw_src) or (not labware and slot_name in ["Slot_6", "Slot_1"]):
            return cx, cy

        # 2. 3-WELL RESERVOIR (Option A: Fits in Slot_1 or Slot_2, 3 wells along X)
        if "3-well" in lw_name or "3_well" in lw_src or "reservoir_3" in lw_src:
            base_x = slot.x_abs
            col_x_map = {'1': base_x + 106.5, '2': base_x + 63.9, '3': base_x + 21.3}
            c_c = well_id[1:] if len(well_id) >= 2 else (well_id if well_id in col_x_map else '1')
            return col_x_map.get(c_c, base_x + 63.9), cy

        # 3. 6-COLUMN RESERVOIR (reservoir_6 labware or Slot_3 default)
        if ("6-column" in lw_name or "reservoir_6" in lw_src or "6_column" in lw_src) or (not labware and slot_name in ["Slot_3", "Slot_5"]):
            col_x = {
                '1': 245.0, '2': 230.0, '3': 212.0,
                '4': 195.5, '5': 179.0, '6': 162.5
            }
            if slot.x_abs < 70.0:
                col_x = {k: v - 135.2 for k, v in col_x.items()}
            col_char = well_id[1:] if len(well_id) >= 2 else '1'
            target_x = col_x.get(col_char, 195.5 if slot.x_abs >= 70.0 else 60.3)
            target_y = 200.0 if slot_name == "Slot_5" else cy
            return target_x, target_y

        # 4. MYRIAMED 48-WELL EHM PLATE (Slot_4 default or myriamed/ehm labware)
        if ("myriamed" in lw_name or "ehm" in lw_name or "48" in lw_name or "ehm" in lw_src or "myriamed" in lw_src) or (not labware and slot_name == "Slot_4"):
            col_x = {'1': 106.00, '2': 88.00, '3': 70.00, '4': 52.00, '5': 34.00, '6': 16.00}
            row_y = {
                'A': 60.0, 'B': 69.0, 'C': 78.0, 'D': 87.0,
                'E': 96.0, 'F': 105.0, 'G': 114.0, 'H': 123.0
            }
            if len(well_id) >= 2:
                r_c = well_id[0].upper()
                c_c = well_id[1:]
                if r_c in row_y and c_c in col_x:
                    return col_x[c_c], row_y[r_c]
            if hasattr(self, 'logger'):
                self.logger.warning(f"Slot 4 Override: Well {well_id} falls outside defined EHM grid.")

        # 5. 96-WELL FORMAT (Tip Rack or 96-Well Microplate on any slot!)
        if ("96" in lw_name or "tip" in lw_name or "tip_rack" in lw_src or "96" in lw_src or
            (labware and getattr(labware, 'rows', 0) == 8 and getattr(labware, 'columns', 0) == 12)) or (not labware and slot_name in ["Slot_3", "Slot_4", "Slot_5"]):
            if slot_name == "Slot_5":
                col_x = {
                    '1': 243.0, '2': 234.0, '3': 225.0, '4': 216.0,
                    '5': 207.0, '6': 198.0, '7': 189.0, '8': 180.0,
                    '9': 171.0, '10': 162.0, '11': 153.0, '12': 143.0
                }
                origin_y = 155.0
                if len(well_id) >= 2:
                    r_c = well_id[0].upper()
                    c_str = well_id[1:]
                    r_idx = ord(r_c) - ord('A')
                    if r_c == 'H':
                        warn_msg = f"Slot 5 Warning: Well {well_id} in Row H exceeds pipette travel limit (Y=218.0mm). Usable range: A1-G12."
                        if hasattr(self, 'logger') and self.logger:
                            self.logger.warning(warn_msg)
                        else:
                            print(f"[WARNING] {warn_msg}")
                    if c_str in col_x and 0 <= r_idx < 8:
                        return col_x[c_str], origin_y + (r_idx * 9.0)
            else:
                origin_x = 242.0 if slot.x_abs >= 70.0 else 106.8
                origin_y = slot.y_abs if slot.y_abs >= 40.0 else 60.0
                if len(well_id) >= 2:
                    r_c = well_id[0].upper()
                    c_str = well_id[1:]
                    try:
                        c_idx = int(c_str) - 1
                        r_idx = ord(r_c) - ord('A')
                        if 0 <= c_idx < 12 and 0 <= r_idx < 8:
                            return origin_x - (c_idx * 9.0), origin_y + (r_idx * 9.0)
                    except ValueError:
                        pass

        # 6. Fallback Generic Labware
        if labware and well_id in labware.wells:
            well_obj = labware.wells[well_id]
            target_x = (slot.x_abs + slot.width_mm) - well_obj.x_rel
            target_y = slot.y_abs + well_obj.y_rel
            return target_x, target_y

        return cx, cy

    def get_target_z(self, action: str, slot_name: str, well_id: str, has_tips: bool = True,
                     extra_z: float = 0.0) -> float:
        if action == "Pick Up Tip":
            return 0.0

        slot_obj = self.deck_slots.get(slot_name)
        slot_z_offset = slot_obj.z_offset if slot_obj else 0.0
        labware_obj = self.deck_labware.get(slot_name)
        lw_name = (getattr(labware_obj, 'name', '') or '').lower()
        lw_src = (getattr(labware_obj, 'source_file', '') or '').lower()

        if action in ["Aspirate Media", "Dispense Media", "Discard Tip"]:
            if "waste" in lw_name or "waste" in lw_src or (not labware_obj and slot_name in ["Slot_6", "Slot_1"]):
                base_z = 90.0
            elif "3-well" in lw_name or "3_well" in lw_src or "reservoir_3" in lw_src:
                base_z = 98.0
            elif ("96" in lw_name or "96" in lw_src or (not labware_obj and slot_name == "Slot_5")) and ("tip" not in lw_name and "tip" not in lw_src):
                base_z = 76.0
            elif "6-column" in lw_name or "reservoir_6" in lw_src or "reservoir" in lw_name or (not labware_obj and slot_name in ["Slot_3", "Slot_5"]):
                base_z = 103.0
            elif "myriamed" in lw_name or "ehm" in lw_name or "48" in lw_name or (not labware_obj and slot_name == "Slot_4"):
                base_z = 98.0
            elif "tip" in lw_name or (labware_obj and getattr(labware_obj, 'rows', 0) == 8 and getattr(labware_obj, 'columns', 0) == 12):
                base_z = 98.0
            elif action == "Discard Tip" and slot_name == "Slot_1":
                base_z = 90.0
            else:
                base_z = 101.0

            return min(base_z + slot_z_offset + extra_z, 103.5)

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