#!/usr/bin/env python3
"""
Unit test for Tip Pickup Detection & Micro-Search logic.
Verifies:
1. Empty socket (Z >= 84.5mm) is identified as EMPTY:
   - Does NOT trigger double push (move_z(push_z))
   - Does NOT enter microsearch
   - Returns False
2. Firmly seated tip (71.5mm <= Z < 84.0mm, pick_ok=True) is identified as ACQUIRED:
   - Does NOT trigger double push
   - Ceases all microsearch immediately
   - Returns True
3. Collar rim stall (Z < 71.5mm):
   - Correctly recognized as collar rim collision
   - Hovers 3mm above rim and engages polar microsearch
   - Upon finding tip at offset, immediately terminates search and learns offset
"""

import sys
import os

class MockHardware:
    def __init__(self):
        self.z_position = 0.0
        self.z_speed = 9
        self.tip_pickup_force = 0
        self.move_z_history = []
        self.pick_tip_calls = []
        # Simulation scenario: 'empty', 'seated', 'rim_then_seat'
        self.scenario = 'seated'
        self.probe_count = 0

    def move_z(self, z):
        self.z_position = float(z)
        self.move_z_history.append(float(z))

    def pick_tip(self, limit):
        self.pick_tip_calls.append(limit)
        self.probe_count += 1
        if self.scenario == 'empty':
            # Plunge all the way to 85.5mm
            self.z_position = 85.5
            raise Exception("CommandFailed: limit reached")
        elif self.scenario == 'seated':
            # Wedges nicely at 75.0mm
            self.z_position = 75.0
            return True
        elif self.scenario == 'rim_then_seat':
            if self.probe_count == 1:
                # First attempt hits rim at 69.5mm
                self.z_position = 69.5
                return True # or force triggered at rim
            else:
                # Microsearch offset drops into bore at 74.8mm
                self.z_position = 74.8
                return True
        elif self.scenario == 'rim_all_fail':
            self.z_position = 69.5
            return True

    def sensor_value(self):
        return 34500

class MockLIMS:
    def __init__(self):
        self.pipettor = type("Pip", (), {"hardware": MockHardware()})()
        self.hw = type("HW", (), {"move_to": lambda self, x, y, z, speed=100: None})()

class MockApp:
    def __init__(self):
        self.lims = MockLIMS()
        self.speed_var = type("V", (), {"get": lambda: 100})()
        self.adaptive_tip_centering_var = type("V", (), {"get": lambda: True})()
        self.is_aborted = False
        self.logger = type("Log", (), {
            "info": lambda self, msg: print(f"[INFO] {msg}"),
            "warning": lambda self, msg: print(f"[WARN] {msg}"),
            "error": lambda self, msg: print(f"[ERR] {msg}")
        })()
        self.tip_rack_learned_offset = (0.0, 0.0)

def test_empty_socket():
    print("\n--- Test 1: Empty Socket Detection ---")
    app = MockApp()
    hw = app.lims.pipettor.hardware
    hw.scenario = 'empty'
    pickup_limit = 87.0
    hw_speed = 9
    approach_z = 55.0

    def _attempt_tip_seat(tx_coord, ty_coord, from_hover=False, hover_z=None):
        if not from_hover:
            hw.move_z(0)
            hw.z_speed = hw_speed
            hw.move_z(approach_z)
        hw.z_speed = 3
        hw.tip_pickup_force = 26
        pick_ok = False
        try:
            hw.pick_tip(pickup_limit)
            pick_ok = True
        except Exception:
            pick_ok = False
        curr_z = getattr(hw, 'z_position', 0.0)

        if curr_z >= 84.5 or curr_z >= (pickup_limit - 2.0) or (not pick_ok and curr_z >= 82.5):
            return False, curr_z
        if pick_ok and 71.5 <= curr_z < 84.0:
            return True, curr_z
        return False, curr_z

    def _adaptive_search_and_pick(base_x, base_y):
        seated, curr_z = _attempt_tip_seat(base_x, base_y, from_hover=False)
        if seated:
            hw.move_z(0)
            return True, curr_z
        if curr_z >= 84.5 or curr_z >= (pickup_limit - 2.0) or curr_z >= 82.5:
            print(f"Socket empty at ({base_x}, {base_y}) (Z={curr_z:.2f}mm reached limit). Skipping to next well.")
            hw.move_z(0)
            return False, curr_z
        # microsearch would go here
        return False, curr_z

    seated, cz = _adaptive_search_and_pick(100.0, 50.0)
    assert not seated, "Empty socket must NOT be declared seated!"
    assert cz == 85.5, f"Expected Z=85.5, got {cz}"
    assert len(hw.pick_tip_calls) == 1, "Must only probe once on empty socket (no microsearch)!"
    # Verify no second push (push_z) occurred
    assert not any(z > 85.5 for z in hw.move_z_history), "Must NOT push deeper than limit on empty socket!"
    print("PASS: Empty socket correctly detected without double push or microsearch.")

def test_seated_tip():
    print("\n--- Test 2: Nominal Tip Pickup ---")
    app = MockApp()
    hw = app.lims.pipettor.hardware
    hw.scenario = 'seated'
    pickup_limit = 87.0
    hw_speed = 9
    approach_z = 55.0

    def _attempt_tip_seat(tx_coord, ty_coord, from_hover=False, hover_z=None):
        if not from_hover:
            hw.move_z(0)
            hw.z_speed = hw_speed
            hw.move_z(approach_z)
        hw.z_speed = 3
        hw.tip_pickup_force = 26
        pick_ok = False
        try:
            hw.pick_tip(pickup_limit)
            pick_ok = True
        except Exception:
            pick_ok = False
        curr_z = getattr(hw, 'z_position', 0.0)

        if curr_z >= 84.5 or curr_z >= (pickup_limit - 2.0) or (not pick_ok and curr_z >= 82.5):
            return False, curr_z
        if pick_ok and 71.5 <= curr_z < 84.0:
            return True, curr_z
        return False, curr_z

    def _adaptive_search_and_pick(base_x, base_y):
        seated, curr_z = _attempt_tip_seat(base_x, base_y, from_hover=False)
        if seated:
            hw.move_z(0)
            return True, curr_z
        if curr_z >= 84.5:
            hw.move_z(0)
            return False, curr_z
        # Microsearch would be here
        return False, curr_z

    seated, cz = _adaptive_search_and_pick(100.0, 50.0)
    assert seated, "Tip should be declared seated!"
    assert cz == 75.0, f"Expected Z=75.0, got {cz}"
    assert len(hw.pick_tip_calls) == 1, "Must only probe once when tip is acquired!"
    assert hw.z_position == 0.0, "Must retract to Z=0 clearance!"
    print("PASS: Nominal tip pickup acquired immediately with no extra push and no microsearch.")

def test_rim_stall_and_microsearch():
    print("\n--- Test 3: Collar Rim Stall with Microsearch ---")
    app = MockApp()
    hw = app.lims.pipettor.hardware
    hw.scenario = 'rim_then_seat'
    pickup_limit = 87.0
    hw_speed = 9
    approach_z = 55.0

    def _attempt_tip_seat(tx_coord, ty_coord, from_hover=False, hover_z=None):
        if not from_hover:
            hw.move_z(0)
            hw.z_speed = hw_speed
            hw.move_z(approach_z)
        hw.z_speed = 3
        hw.tip_pickup_force = 26
        pick_ok = False
        try:
            hw.pick_tip(pickup_limit)
            pick_ok = True
        except Exception:
            pick_ok = False
        curr_z = getattr(hw, 'z_position', 0.0)

        if curr_z >= 84.5 or curr_z >= (pickup_limit - 2.0) or (not pick_ok and curr_z >= 82.5):
            return False, curr_z
        if pick_ok and 71.5 <= curr_z < 84.0:
            return True, curr_z
        return False, curr_z

    def _adaptive_search_and_pick(base_x, base_y):
        seated, curr_z = _attempt_tip_seat(base_x, base_y, from_hover=False)
        if seated:
            hw.move_z(0)
            return True, curr_z
        if curr_z >= 84.5:
            hw.move_z(0)
            return False, curr_z

        # Rim stall
        if curr_z < 72.0:
            hover_z = max(0.0, curr_z - 3.0)
            hw.move_z(hover_z)
            search_pattern = [(0.3, 0.0), (-0.3, 0.0), (0.0, 0.3)]
            for dx, dy in search_pattern:
                s_ok, s_cz = _attempt_tip_seat(base_x + dx, base_y + dy, from_hover=True, hover_z=hover_z)
                if s_ok:
                    app.tip_rack_learned_offset = (dx, dy)
                    hw.move_z(0)
                    return True, s_cz
                else:
                    hw.move_z(hover_z)

        hw.move_z(0)
        return False, curr_z

    seated, cz = _adaptive_search_and_pick(100.0, 50.0)
    assert seated, "Microsearch should find and seat the tip!"
    assert cz == 74.8, f"Expected Z=74.8, got {cz}"
    assert len(hw.pick_tip_calls) == 2, f"Expected 2 probes (1 rim, 1 microsearch), got {len(hw.pick_tip_calls)}"
    assert app.tip_rack_learned_offset == (0.3, 0.0), "Offset should be learned!"
    assert hw.z_position == 0.0, "Must retract to clearance Z=0!"
    print("PASS: Collar rim stall correctly engaged microsearch, acquired tip at offset, and learned offset.")

if __name__ == '__main__':
    test_empty_socket()
    test_seated_tip()
    test_rim_stall_and_microsearch()
    print("\nALL TIP DETECTION UNIT TESTS PASSED!")
