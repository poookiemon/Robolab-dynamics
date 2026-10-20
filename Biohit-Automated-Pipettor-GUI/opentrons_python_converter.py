import sys
import os
import types

class MockWell:
    def __init__(self, name, labware):
        self.name = name
        self.labware = labware

    def bottom(self, offset=0):
        return self

    def top(self, offset=0):
        return self

    def __repr__(self):
        return f"{getattr(self.labware, 'name', 'lw')}:{self.name}"

class MockLabware:
    def __init__(self, name, location):
        self.name = name
        self.location = str(location)
        self._wells = {}
        # Prepopulate standard grid wells
        for r in 'ABCDEFGH':
            for c in range(1, 13):
                w_name = f"{r}{c}"
                self._wells[w_name] = MockWell(w_name, self)

    def __getitem__(self, item):
        if isinstance(item, str):
            if item not in self._wells:
                self._wells[item] = MockWell(item, self)
            return self._wells[item]
        elif isinstance(item, int):
            keys = list(self._wells.keys())
            if item < len(keys):
                return self._wells[keys[item]]
            return MockWell(f"W{item}", self)
        return self._wells.get(str(item), MockWell(str(item), self))

    def wells(self):
        return list(self._wells.values())

    def wells_by_name(self):
        return self._wells

    def rows(self):
        res = {}
        for r in 'ABCDEFGH':
            res[r] = [self._wells[f"{r}{c}"] for c in range(1, 13)]
        return res

    def columns(self):
        res = {}
        for c in range(1, 13):
            res[str(c)] = [self._wells[f"{r}{c}"] for r in 'ABCDEFGH']
        return res

    def load_liquid(self, *args, **kwargs):
        pass

class MockPipette:
    def __init__(self, name, mount, protocol, max_volume=200.0):
        self.name = name
        self.mount = mount
        self.protocol = protocol
        self.max_volume = float(max_volume)
        self.has_tip = False
        self.tip_index = 0

    def _next_tip(self):
        r = chr(ord('A') + (self.tip_index // 12))
        c = (self.tip_index % 12) + 1
        self.tip_index = (self.tip_index + 1) % 96
        return f"{r}{c}"

    def pick_up_tip(self, location=None):
        well = location.name if isinstance(location, MockWell) else self._next_tip()
        self.has_tip = True
        slot = self.protocol.tip_slot
        self.protocol.record_step("Pick Up Tip", slot, well, 0.0)

    def drop_tip(self, location=None):
        self.has_tip = False
        slot = self.protocol.waste_slot
        self.protocol.record_step("Discard Tip", slot, "A1", 0.0)

    def return_tip(self):
        self.drop_tip()

    def _get_target(self, target):
        if isinstance(target, MockWell):
            slot = self.protocol.map_slot(target.labware.location)
            lw_name = getattr(target.labware, 'name', '').lower()
            if "tuberack" in lw_name or "falcon" in lw_name:
                if target.name.upper() == "A4":
                    return self.protocol.waste_slot, "A1"
                elif target.name.upper() == "A3":
                    return slot, "A1"
            return slot, target.name
        elif isinstance(target, MockLabware):
            return self.protocol.map_slot(target.location), "A1"
        return self.protocol.waste_slot, "A1"

    def _extract_mix_info(self, kwargs):
        mix_after = kwargs.get('mix_after')
        if isinstance(mix_after, (tuple, list)) and len(mix_after) >= 2:
            return 5, float(mix_after[1])
        lc = kwargs.get('liquid_class')
        if isinstance(lc, dict):
            found_reps = 0
            found_vol = 100.0
            def walk(d):
                nonlocal found_reps, found_vol
                if isinstance(d, dict):
                    if "mix" in d and isinstance(d["mix"], dict) and d["mix"].get("enabled"):
                        found_reps += int(d["mix"].get("repetitions", 5))
                        found_vol = float(d["mix"].get("volume", 100.0))
                    for v in d.values():
                        walk(v)
            walk(lc)
            if found_reps > 0:
                return 5, found_vol
        return 0, 100.0

    def aspirate(self, volume=None, location=None, **kwargs):
        vol = float(volume) if volume is not None else self.max_volume
        slot, well = self._get_target(location)
        self.protocol.record_step("Aspirate Media", slot, well, vol)

    def dispense(self, volume=None, location=None, **kwargs):
        vol = float(volume) if volume is not None else self.max_volume
        slot, well = self._get_target(location)
        self.protocol.record_step("Dispense Media", slot, well, vol)

    def mix(self, repetitions=5, volume=None, location=None, **kwargs):
        vol = float(volume) if volume is not None else 100.0
        reps = max(1, int(repetitions)) if repetitions else 5
        if self.protocol.steps and self.protocol.steps[-1].get("action") == "Dispense Media":
            self.protocol.steps[-1]["mix_cycles"] = reps
            self.protocol.steps[-1]["mix_volume"] = round(vol, 2)
        else:
            slot, well = self._get_target(location)
            self.protocol.record_step("Mix Well", slot, well, vol, mix_cycles=reps, mix_volume=vol)

    def blow_out(self, location=None):
        pass

    def touch_tip(self, location=None, **kwargs):
        pass

    def air_gap(self, volume=None, **kwargs):
        pass

    def distribute_with_liquid_class(self, volume, source, dest, **kwargs):
        self.distribute(volume, source, dest, **kwargs)

    def transfer_with_liquid_class(self, volume, source, dest, **kwargs):
        self.transfer(volume, source, dest, **kwargs)

    def distribute(self, volume, source, dest, **kwargs):
        new_tip = kwargs.get('new_tip', 'once')
        tips = kwargs.get('tips', [])
        
        if (new_tip in ['once', 'always'] and not self.has_tip) or new_tip == 'always':
            tip_well = tips[0].name if tips and isinstance(tips[0], MockWell) else self._next_tip()
            self.has_tip = True
            self.protocol.record_step("Pick Up Tip", self.protocol.tip_slot, tip_well, 0.0)

        src = source[0] if isinstance(source, list) else source
        s_slot, s_well = self._get_target(src)
        dest_list = dest if isinstance(dest, list) else [dest]

        vol = float(volume)
        # Multi-dispense optimization: if 2 * vol <= max_volume (e.g. 2 * 100uL = 200uL), aspirate 200uL once and dispense 100uL + 100uL
        if vol > 0 and (vol * 2.0) <= self.max_volume and len(dest_list) >= 2:
            idx = 0
            while idx < len(dest_list):
                if idx + 1 < len(dest_list):
                    d1_slot, d1_well = self._get_target(dest_list[idx])
                    d2_slot, d2_well = self._get_target(dest_list[idx + 1])
                    self.protocol.record_step("Aspirate Media", s_slot, s_well, vol * 2.0)
                    self.protocol.record_step("Dispense Media", d1_slot, d1_well, vol, no_blowout=True, labware="generic_96_well_plate.json" if d1_slot == "Slot_4" else None)
                    self.protocol.record_step("Dispense Media", d2_slot, d2_well, vol, no_blowout=False, labware="generic_96_well_plate.json" if d2_slot == "Slot_4" else None)
                    idx += 2
                else:
                    d_slot, d_well = self._get_target(dest_list[idx])
                    self.protocol.record_step("Aspirate Media", s_slot, s_well, vol)
                    self.protocol.record_step("Dispense Media", d_slot, d_well, vol, labware="generic_96_well_plate.json" if d_slot == "Slot_4" else None)
                    idx += 1
        else:
            for d in dest_list:
                d_slot, d_well = self._get_target(d)
                # Volume chunking
                rem = vol
                while rem > 0:
                    chunk = min(rem, self.max_volume)
                    self.protocol.record_step("Aspirate Media", s_slot, s_well, chunk)
                    self.protocol.record_step("Dispense Media", d_slot, d_well, chunk, labware="generic_96_well_plate.json" if d_slot == "Slot_4" else None)
                    rem -= chunk

        if new_tip == 'always':
            self.drop_tip()

    def transfer(self, volume, source, dest, **kwargs):
        new_tip = kwargs.get('new_tip', 'once')
        tips = kwargs.get('tips', [])
        src_list = source if isinstance(source, list) else [source]
        dest_list = dest if isinstance(dest, list) else [dest]
        mix_cycles, mix_vol = self._extract_mix_info(kwargs)

        # Match lengths if one is single and other is list
        if len(src_list) == 1 and len(dest_list) > 1:
            src_list = src_list * len(dest_list)
        elif len(dest_list) == 1 and len(src_list) > 1:
            dest_list = dest_list * len(src_list)

        vol = float(volume)
        for s, d in zip(src_list, dest_list):
            if (new_tip in ['once', 'always'] and not self.has_tip) or new_tip == 'always':
                tip_well = tips[0].name if tips and isinstance(tips[0], MockWell) else self._next_tip()
                self.has_tip = True
                self.protocol.record_step("Pick Up Tip", self.protocol.tip_slot, tip_well, 0.0)

            s_slot, s_well = self._get_target(s)
            d_slot, d_well = self._get_target(d)

            rem = vol
            while rem > 0:
                chunk = min(rem, self.max_volume)
                self.protocol.record_step("Aspirate Media", s_slot, s_well, chunk, labware="generic_96_well_plate.json" if s_slot == "Slot_4" else None)
                is_last = (rem - chunk) <= 0
                self.protocol.record_step(
                    "Dispense Media", d_slot, d_well, chunk,
                    mix_cycles=(mix_cycles if is_last else 0),
                    mix_volume=mix_vol,
                    labware="generic_96_well_plate.json" if d_slot == "Slot_4" else None
                )
                rem -= chunk

            if new_tip == 'always':
                self.drop_tip()

    def consolidate(self, volume, source, dest, **kwargs):
        new_tip = kwargs.get('new_tip', 'once')
        tips = kwargs.get('tips', [])
        src_list = source if isinstance(source, list) else [source]

        if (new_tip in ['once', 'always'] and not self.has_tip) or new_tip == 'always':
            tip_well = tips[0].name if tips and isinstance(tips[0], MockWell) else self._next_tip()
            self.has_tip = True
            self.protocol.record_step("Pick Up Tip", self.protocol.tip_slot, tip_well, 0.0)

        d_slot, d_well = self._get_target(dest)
        vol = float(volume)

        for s in src_list:
            s_slot, s_well = self._get_target(s)
            rem = vol
            while rem > 0:
                chunk = min(rem, self.max_volume)
                self.protocol.record_step("Aspirate Media", s_slot, s_well, chunk)
                self.protocol.record_step("Dispense Media", d_slot, d_well, chunk)
                rem -= chunk

        if new_tip == 'always':
            self.drop_tip()

class MockProtocolContext:
    def __init__(self, slot_map=None, max_volume=200.0):
        self.slot_map = slot_map or {}
        self.max_volume = float(max_volume)
        self.tip_slot = "Slot_3"
        self.waste_slot = "Slot_6"
        self.labware_list = {}
        self.fixed_trash = MockLabware("fixed_trash", "12")
        self.steps = []
        self.metadata = {}

    def map_slot(self, ot_slot):
        s_str = str(ot_slot)
        if s_str in self.slot_map:
            return self.slot_map[s_str]
        # Fallback heuristic if not explicitly mapped:
        if s_str in ["1", "2", "3", "4", "5", "6"]:
            return f"Slot_{s_str}"
        return "Slot_4"

    def load_labware(self, name, location, **kwargs):
        lw = MockLabware(name, location)
        self.labware_list[str(location)] = lw
        return lw

    def load_instrument(self, name, mount, **kwargs):
        return MockPipette(name, mount, self, max_volume=self.max_volume)

    def define_liquid(self, *args, **kwargs):
        return None

    def define_liquid_class(self, *args, **kwargs):
        return kwargs.get("properties", {})

    def delay(self, seconds=0, minutes=0, **kwargs):
        total_sec = float(seconds) + (float(minutes) * 60.0)
        if total_sec > 0:
            self.record_step("System: Incubate (Wait)", "Slot_1", "A1", total_sec)

    def pause(self, msg=""):
        self.delay(seconds=1)

    def comment(self, msg=""):
        pass

    def record_step(self, action, slot, well, volume, mix_cycles=0, mix_volume=100.0, no_blowout=False, labware=None):
        step = {
            "action": action,
            "mode": "auto",
            "slot": slot,
            "well": well,
            "volume": round(float(volume), 2),
            "extra_z": 0.0
        }
        if mix_cycles > 0:
            step["mix_cycles"] = int(mix_cycles)
            step["mix_volume"] = round(float(mix_volume), 2)
        if no_blowout:
            step["no_blowout"] = True
        if labware:
            step["labware"] = labware
        self.steps.append(step)

def detect_opentrons_labware(py_filepath):
    """
    Scans a python protocol file to extract loaded labware definitions
    and returns a list of dictionaries: [{'name': ..., 'slot': ..., 'suggested_biohit_slot': ...}]
    """
    detected = []
    # Inject mock opentrons modules
    mock_ot = types.ModuleType('opentrons')
    mock_protocol_api = types.ModuleType('opentrons.protocol_api')
    mock_types = types.ModuleType('opentrons.types')

    mock_protocol_api.ProtocolContext = MockProtocolContext
    mock_ot.protocol_api = mock_protocol_api
    mock_ot.types = mock_types

    old_ot = sys.modules.get('opentrons')
    old_papi = sys.modules.get('opentrons.protocol_api')
    old_types = sys.modules.get('opentrons.types')

    sys.modules['opentrons'] = mock_ot
    sys.modules['opentrons.protocol_api'] = mock_protocol_api
    sys.modules['opentrons.types'] = mock_types

    try:
        proto = MockProtocolContext()
        with open(py_filepath, 'r', encoding='utf-8') as f:
            code = f.read()

        globs = {'__name__': '__main__'}
        exec(code, globs)
        run_func = globs.get('run')

        if run_func:
            # Fake execution just to collect labware
            class LabwareCollector(MockProtocolContext):
                def load_instrument(self, *args, **kwargs):
                    return None
            collector = LabwareCollector()
            try:
                run_func(collector)
            except Exception:
                pass

            for slot, lw in collector.labware_list.items():
                lw_lower = lw.name.lower()
                if "tip" in lw_lower or slot == "8":
                    suggested = "Slot_3"
                elif "tuberack" in lw_lower or "falcon" in lw_lower or "reservoir" in lw_lower or "trough" in lw_lower or slot == "10":
                    suggested = "Slot_2"
                elif "waste" in lw_lower or "trash" in lw_lower or slot == "12":
                    suggested = "Slot_6"
                elif slot == "4":
                    suggested = "Slot_4"
                elif slot == "11":
                    suggested = "Slot_5"
                else:
                    suggested = "Slot_4" if "Slot_4" not in [d.get('suggested_biohit_slot') for d in detected] else "Slot_5"

                detected.append({
                    "name": lw.name,
                    "opentrons_slot": slot,
                    "suggested_biohit_slot": suggested
                })
    finally:
        if old_ot: sys.modules['opentrons'] = old_ot
        elif 'opentrons' in sys.modules: del sys.modules['opentrons']
        if old_papi: sys.modules['opentrons.protocol_api'] = old_papi
        elif 'opentrons.protocol_api' in sys.modules: del sys.modules['opentrons.protocol_api']
        if old_types: sys.modules['opentrons.types'] = old_types
        elif 'opentrons.types' in sys.modules: del sys.modules['opentrons.types']

    return detected

def convert_opentrons_py_to_biohit(py_filepath, slot_mapping=None, max_volume=200.0):
    """
    Executes an Opentrons Python protocol against our mock environment,
    translating it into native Biohit JSON protocol steps.
    """
    mock_ot = types.ModuleType('opentrons')
    mock_protocol_api = types.ModuleType('opentrons.protocol_api')
    mock_types = types.ModuleType('opentrons.types')

    mock_protocol_api.ProtocolContext = MockProtocolContext
    mock_ot.protocol_api = mock_protocol_api
    mock_ot.types = mock_types

    old_ot = sys.modules.get('opentrons')
    old_papi = sys.modules.get('opentrons.protocol_api')
    old_types = sys.modules.get('opentrons.types')

    sys.modules['opentrons'] = mock_ot
    sys.modules['opentrons.protocol_api'] = mock_protocol_api
    sys.modules['opentrons.types'] = mock_types

    try:
        # Default slot map if none provided
        effective_slot_map = {
            '8': 'Slot_3',
            '10': 'Slot_2',
            '4': 'Slot_4',
            '11': 'Slot_5',
            '12': 'Slot_6'
        }
        if slot_mapping:
            effective_slot_map.update(slot_mapping)

        proto = MockProtocolContext(slot_map=effective_slot_map, max_volume=max_volume)
        
        # Look up metadata from tip rack if in slot_map
        for ot_slot, bio_slot in effective_slot_map.items():
            if bio_slot == 'Slot_3':
                proto.tip_slot = 'Slot_3'
            elif bio_slot == 'Slot_6':
                proto.waste_slot = 'Slot_6'

        with open(py_filepath, 'r', encoding='utf-8') as f:
            code = f.read()

        globs = {'__name__': '__main__'}
        exec(code, globs)
        run_func = globs.get('run')
        if not run_func:
            raise ValueError("Protocol does not define a 'run(protocol)' function.")

        run_func(proto)
        return proto.steps
    finally:
        if old_ot: sys.modules['opentrons'] = old_ot
        elif 'opentrons' in sys.modules: del sys.modules['opentrons']
        if old_papi: sys.modules['opentrons.protocol_api'] = old_papi
        elif 'opentrons.protocol_api' in sys.modules: del sys.modules['opentrons.protocol_api']
        if old_types: sys.modules['opentrons.types'] = old_types
        elif 'opentrons.types' in sys.modules: del sys.modules['opentrons.types']
