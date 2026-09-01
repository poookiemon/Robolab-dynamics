import time
import subprocess
import sys
import ctypes  # Native Windows library for ghost mouse
from working import LIMSOrchestrator, Labware, Pipettor

hardware_pipettor = Pipettor(tip_volume=200, multichannel=True)
lims = LIMSOrchestrator(hardware=hardware_pipettor)

try:
    lims.load_deck_profile("deck_calibration.json")
    lims.load_liquid_classes("liquid_classes.json")

    ehm_plate = Labware("labware/corning_96_flat.json")
    calcium_reservoir = Labware("labware/reservoir_6_column.json")
    waste_trough = Labware("labware/waste_trough.json")

    lims.assign_labware_to_slot("Slot_2", ehm_plate)
    lims.assign_labware_to_slot("Slot_4", calcium_reservoir)
    lims.assign_labware_to_slot("Slot_6", waste_trough)

    incubation_time = 300
    platename = '2026_Ca_Curve_Run1'
    bDoFoc = False

    reservoir_0mM = "A4"

    print("Starting Calcium-force curve protocol.")

    for target_well in ["A1", "A3", "A6"]:
        lims.execute_transfer(
            source_slot="Slot_2",
            source_well=target_well,
            dest_slot="Slot_6",
            dest_well="A1",
            volume=600.0,
            liquid_class_name="Cell_Medium_Standard"
        )

        lims.execute_transfer(
            source_slot="Slot_4",
            source_well=reservoir_0mM,
            dest_slot="Slot_2",
            dest_well=target_well,
            volume=450.0,
            liquid_class_name="Calcium_Solution_0mM"
        )

    print("Fill cycle complete.")

    if bDoFoc:
        print(f"Incubating for {incubation_time / 60} minutes...")
        time.sleep(incubation_time)

        print("Executing mandatory safe Z-retraction...")
        if lims.pipettor.hardware and lims.hw.is_initialized:
            try:
                lims.pipettor.hardware.move_z(0)
                print("Z-axis secured at clearance height.")
            except Exception as e:
                print(f"CRITICAL WARNING: Z-Retract failed. Halting before measurement. Error: {e}")
                sys.exit(1)

        print("Triggering measurement...")
        try:
            # Launch FOC48 in the background
            p = subprocess.Popen([r'C:\Labhub\Import\FOC48_20240227.exe', r'C:\Labhub\Import\myrPlate_Stim_0.xml', platename])

            print("Waiting for software GUI to load...")
            time.sleep(7.0)

            print("Executing automated clicks...")

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

            print("Automation complete. Waiting for measurement software to finish...")
            p.wait()

        except FileNotFoundError:
            print("Error: The FOC48 executable was not found at the specified path.")

    print("Protocol Complete.")

finally:
    print("Releasing hardware locks and cleaning up context...")
    hardware_pipettor.close() 