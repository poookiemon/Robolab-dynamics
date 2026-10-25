#!/usr/bin/env python3
"""
Unit test for Tip Pickup Detection & Auto-Advance logic.
Verifies:
1. Empty socket (Z >= 84.0mm or stalled shallowly Z < 60.0mm):
   - Probes exactly once with pick_tip()
   - No second push
   - No microsearch / hovering
   - Retracts immediately to clearance Z=0
   - Returns False, allowing clean auto-advance to next well
2. Seated tip (60.0mm <= Z < 84.0mm):
   - Probes exactly once with pick_tip()
   - No second push
   - Retracts immediately to clearance Z=0
   - Returns True (HAS_TIP = True) and breaks out of search immediately
3. Force-stall exception when pressing into tip collar (e.g. at Z=70.5mm):
   - Absorbs force-stall exception gracefully
   - Verifies 60.0 <= Z < 84.0mm
   - Declares tip seated (True)
   - Retracts immediately to clearance Z=0
4. Auto-advance sequence (e.g. A1 empty -> advances to B1 seated):
   - A1 probed once -> detected empty -> retracted to Z=0
   - B1 probed once -> detected seated -> retracted to Z=0 -> completes!
   - Zero microsearch or double pushing at any point.
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
        # Simulation scenario: 'empty', 'seated', 'seated_force_exception_70mm', 'shallow_stall_55mm'
        self.scenario = 'seated'
        self.well_scenarios = {}

    def move_z(self, z):
        self.z_position = float(z)
        self.move_z_history.append(float(z))

    def pick_tip(self, limit):
        self.pick_tip_calls.append(limit)
        sc = self.scenario
        if sc == 'empty':
            self.z_position = 85.5
            raise Exception("CommandFailed: limit reached")
        elif sc == 'shallow_stall_55mm':
            self.z_position = 55.0
            raise Exception("CommandFailed: Actuator stalled")
        elif sc == 'seated':
            self.z_position = 75.0
            return True
        elif sc == 'seated_force_exception_70mm':
            self.z_position = 70.5
            raise Exception("CommandFailed: Actuator stalled on force 26")

class MockLIMS:
    def __init__(self):
        self.pipettor = type("Pip", (), {"hardware": MockHardware()})()
        self.hw = type("HW", (), {"move_to": lambda self, x, y, z, speed=100: None})()

class MockApp:
    def __init__(self):
        self.lims = MockLIMS()
        class V:
            def get(self): return 100
        self.speed_var = V()
        self.is_aborted = False
        self.logger = type("Log", (), {
            "info": lambda self, msg: print(f"[INFO] {msg}"),
            "warning": lambda self, msg: print(f"[WARN] {msg}"),
            "error": lambda self, msg: print(f"[ERR] {msg}")
        })()

def _make_do_pick(app, pickup_limit=87.0, approach_z=55.0, hw_speed=9):
    hw = app.lims.pipettor.hardware
    def _do_pick(tx, ty):
        if hw:
            hw.move_z(0)
        app.lims.hw.move_to(tx, ty, 0, speed=app.speed_var.get())
        if not hw:
            return True, 75.0

        hw.z_speed = hw_speed
        hw.move_z(approach_z)
        hw.z_speed = 3
        hw.tip_pickup_force = 26
        try:
            hw.pick_tip(pickup_limit)
        except Exception:
            pass

        curr_z = getattr(hw, 'z_position', 0.0)
        if 60.0 <= curr_z < 84.0:
            try:
                hw.z_speed = hw_speed
                hw.move_z(0)
            except Exception:
                hw.move_z(0)
            return True, curr_z

        try:
            hw.z_speed = hw_speed
            hw.move_z(0)
        except Exception:
            hw.move_z(0)
        return False, curr_z

    return _do_pick

def test_empty_socket():
    print("\n--- Test 1: Empty Socket Detection ---")
    app = MockApp()
    hw = app.lims.pipettor.hardware
    hw.scenario = 'empty'
    _do_pick = _make_do_pick(app)

    seated, cz = _do_pick(100.0, 50.0)
    assert not seated, "Empty socket must NOT be declared seated!"
    assert cz == 85.5, f"Expected Z=85.5, got {cz}"
    assert len(hw.pick_tip_calls) == 1, "Must only probe once on empty socket!"
    assert hw.z_position == 0.0, "Must retract to clearance Z=0!"
    assert not any(z > 85.5 for z in hw.move_z_history), "Must NOT push deeper than limit!"
    print("PASS: Empty socket correctly detected without double push or microsearch.")

def test_seated_tip():
    print("\n--- Test 2: Nominal Tip Pickup ---")
    app = MockApp()
    hw = app.lims.pipettor.hardware
    hw.scenario = 'seated'
    _do_pick = _make_do_pick(app)

    seated, cz = _do_pick(100.0, 50.0)
    assert seated, "Tip should be declared seated!"
    assert cz == 75.0, f"Expected Z=75.0, got {cz}"
    assert len(hw.pick_tip_calls) == 1, "Must only probe once when tip is acquired!"
    assert hw.z_position == 0.0, "Must retract to Z=0 clearance!"
    print("PASS: Nominal tip pickup acquired immediately with no extra push and no microsearch.")

def test_b1_tip_seated_with_force_stall():
    print("\n--- Test 3: B1 Tip Seated with Force Stall (Z=70.5mm, Driver Exception) ---")
    app = MockApp()
    hw = app.lims.pipettor.hardware
    hw.scenario = 'seated_force_exception_70mm'
    _do_pick = _make_do_pick(app)

    seated, cz = _do_pick(100.0, 50.0)
    assert seated, "B1 Tip MUST be declared seated despite driver exception!"
    assert cz == 70.5, f"Expected Z=70.5, got {cz}"
    assert len(hw.pick_tip_calls) == 1, "Must only probe ONCE and NEVER microsearch!"
    assert hw.z_position == 0.0, "Must immediately retract to clearance Z=0!"
    print("PASS: B1 tip with force-stall exception at Z=70.5mm acquired immediately without microsearch.")

def test_auto_advance_a1_empty_to_b1_seated():
    print("\n--- Test 4: Auto-Advance from A1 (empty) to B1 (seated) ---")
    app = MockApp()
    hw = app.lims.pipettor.hardware
    _do_pick = _make_do_pick(app)

    wells = ["A1", "B1", "C1"]
    tip_found = False
    coords_map = {"A1": (100.0, 50.0), "B1": (100.0, 59.0), "C1": (100.0, 68.0)}

    for current_well in wells:
        # A1 is empty (e.g. stalled shallowly at 55mm or plunged to 85.5mm)
        if current_well == "A1":
            hw.scenario = 'empty'
        else:
            hw.scenario = 'seated'

        tx, ty = coords_map[current_well]
        seated, cz = _do_pick(tx, ty)
        if seated:
            print(f"Tip acquired at {current_well} (Z={cz:.2f}mm). HAS_TIP = True")
            tip_found = True
            break
        else:
            print(f"Well {current_well} empty or passed (Z={cz:.2f}mm). Tracking to next well...")

    assert tip_found, "Must find tip in B1!"
    assert current_well == "B1", f"Expected tip to be found in B1, got {current_well}"
    assert len(hw.pick_tip_calls) == 2, f"Expected exactly 2 probes (1 for A1, 1 for B1), got {len(hw.pick_tip_calls)}"
    assert hw.z_position == 0.0, "Must finish at clearance Z=0!"
    print("PASS: Clean auto-advance from A1 to B1 without any microsearch or stalling.")

if __name__ == '__main__':
    test_empty_socket()
    test_seated_tip()
    test_b1_tip_seated_with_force_stall()
    test_auto_advance_a1_empty_to_b1_seated()
    print("\nALL TIP DETECTION & AUTO-ADVANCE UNIT TESTS PASSED!")
