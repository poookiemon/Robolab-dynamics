import sys
import os
import time
import platform

print("=" * 70)
print(" BIOHIT ROBOT DEEP HARDWARE & MOTOR DIAGNOSTIC ")
print("=" * 70)
print(f"Python: {sys.version.split()[0]} ({platform.architecture()[0]})")
print(f"Platform: {platform.platform()}")
print(f"Working Directory: {os.getcwd()}")

# 1. Test biohit_pipettor import
print("\n[1/6] Checking 'biohit_pipettor' import...")
try:
    import biohit_pipettor
    print(f"  -> SUCCESS: biohit_pipettor loaded from: {biohit_pipettor.__file__}")
except Exception as e:
    print(f"  -> FAILED: Could not import biohit_pipettor: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 2. Test pythonnet and CLR InstrumentLib
print("\n[2/6] Checking .NET CLR and InstrumentLib.dll...")
try:
    import clr
    from os.path import dirname, join
    firmware_path = join(dirname(biohit_pipettor.__file__), "include")
    if firmware_path not in sys.path:
        sys.path.append(firmware_path)
    clr.AddReference("InstrumentLib")
    from InstrumentLib import InstrumentCls
    print("  -> SUCCESS: InstrumentLib.dll loaded successfully.")
except Exception as e:
    print(f"  -> FAILED: CLR / InstrumentLib error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 3. Test InstrumentCls Instantiation & Connection
print("\n[3/6] Instantiating InstrumentCls & Querying Status Registers...")
try:
    inst = InstrumentCls()
    
    # Wait for USB handshake
    connected = False
    for i in range(25):
        time.sleep(0.1)
        if inst.IsConnected():
            connected = True
            break
            
    is_conn = inst.IsConnected()
    usb_conn = getattr(inst.Control.Comm, 'usbConnected', None)
    comm_err = getattr(inst.Control.Comm, 'ErrorCode', None)
    comm_exc = getattr(inst.Control.Comm, 'TheException', None)
    last_err = getattr(inst, 'TheError', None)
    last_exc = getattr(inst, 'TheException', None)
    
    print(f"  -> inst.IsConnected(): {is_conn}")
    print(f"  -> inst.Control.Comm.usbConnected: {usb_conn}")
    print(f"  -> Comm ErrorCode: {comm_err} (0=OK, 1=Port open failed, 2=Timeout, 4=Busy)")
    if comm_exc:
        print(f"  -> Comm Exception: {comm_exc}")
    if last_err:
        print(f"  -> Last Error: '{last_err}'")
    if last_exc:
        print(f"  -> Last Exception: '{last_exc}'")

    if not is_conn:
        print("\n" + "!" * 70)
        print("CRITICAL: Robot USB communication is NOT open!")
        print("Please check:")
        print(" 1. The USB cable is firmly plugged into the PC and the robot.")
        print(" 2. The robot's physical power switch is turned ON.")
        print(" 3. No other application (RoboLine vendor software) is currently open.")
        print("!" * 70)
        sys.exit(1)

except Exception as e:
    print(f"  -> FAILED: Communication error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 4. Check Actuator Detection, Power, & Interlocks
print("\n[4/6] Checking Actuator Detection, Power Supply & Interlocks...")
present_val = -1
door_open = False
estop_active = False
power_missing = False

try:
    present_val = inst.Control.PollPresent()
    print(f"  -> PollPresent Register: {present_val} (bin: {bin(present_val) if present_val >= 0 else 'ERR'})")
    x_present = bool(present_val & 2)
    y_present = bool(present_val & 4)
    z_present = bool(present_val & 8)
    p_present = bool(present_val & 16)
    door_present = bool(present_val & 32)
    print(f"     [Bit 1 / 0x02] X Motor Slave Detected: {x_present}")
    print(f"     [Bit 2 / 0x04] Y Motor Slave Detected: {y_present}")
    print(f"     [Bit 3 / 0x08] Z Motor Slave Detected: {z_present}")
    print(f"     [Bit 4 / 0x10] P Piston Slave Detected: {p_present}")
    print(f"     [Bit 5 / 0x20] Door Sensor Present:    {door_present}")

    if present_val <= 0 or not (x_present and y_present and z_present):
        power_missing = True
        print("\n" + "!" * 70)
        print(">>> CRITICAL WARNING: MOTOR SLAVES NOT DETECTED ON RS-485 BUS! <<<")
        print("The USB interface is powered by PC (5V), but the MOTORS REQUIRE 24V DC!")
        print("Action Required:")
        print(" 1. Verify the 24V DC power brick is plugged into the wall and the robot.")
        print(" 2. Verify the power brick LED is glowing green.")
        print(" 3. Verify the main power rocker switch on the back of the robot is ON.")
        print("!" * 70)

    # Door state check
    try:
        door_state = inst.Control.PollDoorState()
        door_in_use = inst.Control.IsDoorInUse()
        print(f"  -> Door State: {door_state} (0=Closed/OK, 1=OPEN, -1=Error), IsDoorInUse: {door_in_use}")
        if door_state == 1:
            door_open = True
            print("     >>> WARNING: SAFETY DOOR / HOOD IS OPEN! <<<")
            print("     Motors are electrically disabled while the cover is open.")
            print("     Please CLOSE THE FRONT DOOR / LID completely.")
    except Exception as ee:
        print(f"  -> Door query exception: {ee}")

    # Master and Axis Status (mStatus)
    try:
        m_status = inst.Control.PollStatus('M')
        print(f"  -> Master Status (MDS): {m_status} (bin: {bin(m_status) if m_status >= 0 else 'ERR'})")
        if m_status >= 0:
            if m_status & 1:
                print("     [Bit 0 / 0x01] Motor controller error latch is ACTIVE!")
            if m_status & 0x20:
                door_open = True
                print("     [Bit 5 / 0x20] Door Open Interlock ACTIVE!")
            if m_status & 0x40:
                estop_active = True
                print("     [Bit 6 / 0x40] EMERGENCY STOP / STOP BUTTON IS PRESSED!")
        print(f"  -> Status X: {inst.Control.PollStatus('X')}")
        print(f"  -> Status Y: {inst.Control.PollStatus('Y')}")
        print(f"  -> Status Z: {inst.Control.PollStatus('Z')}")
        print(f"  -> Status P: {inst.Control.PollStatus('P')}")
    except Exception as ee:
        print(f"  -> PollStatus exception: {ee}")

    # Latched Error Registers
    try:
        print(f"  -> Error M: {inst.Control.PollError('M')}")
        print(f"  -> Error X: {inst.Control.PollError('X')}")
        print(f"  -> Error Y: {inst.Control.PollError('Y')}")
        print(f"  -> Error Z: {inst.Control.PollError('Z')}")
        print(f"  -> Error P: {inst.Control.PollError('P')}")
        print(f"  -> GetErrors(): '{inst.GetErrors()}'")
        print(f"  -> GetCommErrors(): '{inst.GetCommErrors()}'")
    except Exception as ee:
        print(f"  -> PollError exception: {ee}")

    # Calibrations
    try:
        x_cal = inst.Control.PollCalibration('X')
        y_cal = inst.Control.PollCalibration('Y')
        z_cal = inst.Control.PollCalibration('Z')
        print(f"  -> Calibrations: X={x_cal}, Y={y_cal}, Z={z_cal}")
    except Exception as ee:
        print(f"  -> PollCalibration exception: {ee}")

except Exception as e:
    print(f"  -> Error polling modules: {e}")

# 5. Fault Reset & Motor Homing Test
print("\n[5/6] Resetting Indicators & Testing Physical Motor Drive...")
init_success = False
pos_before = {}
pos_after = {}

try:
    print("  -> Calling ResetIndicators() & RefreshSlaves()...")
    inst.ResetIndicators()
    inst.Control.ResetIndicators()
    inst.Control.RefreshSlaves()
    time.sleep(0.5)

    try:
        pos_before['X'] = inst.PollPosition('X')
        pos_before['Y'] = inst.PollPosition('Y')
        pos_before['Z'] = inst.PollPosition('Z')
        pos_before['P'] = inst.PollPosition('P')
        print(f"  -> Positions BEFORE homing: X={pos_before['X']} mm, Y={pos_before['Y']} mm, Z={pos_before['Z']} mm, P={pos_before['P']}")
    except Exception as ee:
        print(f"  -> Error reading pre-homing position: {ee}")

    print("\n  -> Testing inst.InitializeInstrument() (Native Full Homing)...")
    init_res = inst.InitializeInstrument()
    print(f"     InitializeInstrument() returned: {init_res}")
    time.sleep(1.0)

    print("\n  -> Testing individual axis DriveHome routines:")
    print("     Commanding Z Home (ZRZ)...")
    z_res = inst.Control.DriveHome("Z", True)
    print(f"     Z Home (ZRZ) result: {z_res}")

    print("     Commanding Y Home (YRZ)...")
    y_res = inst.Control.DriveHome("Y", True)
    print(f"     Y Home (YRZ) result: {y_res}")

    print("     Commanding X Home (XRZ)...")
    x_res = inst.Control.DriveHome("X", True)
    print(f"     X Home (XRZ) result: {x_res}")

    print("     Commanding P Home (PRZ30)...")
    p_res = inst.Control.DriveHome("P", True)
    print(f"     P Home (PRZ30) result: {p_res}")

    time.sleep(0.5)
    try:
        pos_after['X'] = inst.PollPosition('X')
        pos_after['Y'] = inst.PollPosition('Y')
        pos_after['Z'] = inst.PollPosition('Z')
        pos_after['P'] = inst.PollPosition('P')
        print(f"\n  -> Positions AFTER homing:  X={pos_after['X']} mm, Y={pos_after['Y']} mm, Z={pos_after['Z']} mm, P={pos_after['P']}")
    except Exception as ee:
        print(f"  -> Error reading post-homing position: {ee}")

    init_success = init_res or (z_res and y_res and x_res)

except Exception as e:
    print(f"  -> Homing routine raised exception: {e}")
    import traceback
    traceback.print_exc()

# 6. Final Diagnostic Summary & Verdict
print("\n" + "=" * 70)
print("[6/6] FINAL DIAGNOSTIC VERDICT")
print("=" * 70)

if init_success and not power_missing and not door_open and not estop_active:
    print(">>> STATUS: ALL MOTORS HOMED SUCCESSFULLY! Hardware is 100% OPERATIONAL. <<<")
    print("The Biohit pipettor is ready for protocols.")
else:
    print(">>> STATUS: HOMING FAILED OR MOTORS DID NOT MOVE! <<<")
    print("\nRoot Cause Breakdown:")
    if power_missing:
        print(" [!] 24V MOTOR POWER IS MISSING:")
        print("     - The robot's USB microcontroller is ON (via PC USB cable), but the motor")
        print("       controllers are NOT receiving 24V DC power.")
        print("     -> Check the external 24V power supply cable plugged into the robot.")
        print("     -> Check the rocker power switch on the robot.")
    if door_open:
        print(" [!] DOOR / HOOD INTERLOCK IS OPEN:")
        print("     - The safety switch reports the door/lid is open (bit 0x20).")
        print("     -> Close the robot front cover completely.")
    if estop_active:
        print(" [!] EMERGENCY STOP IS ENGAGED:")
        print("     - Bit 0x40 is active on the master status register.")
        print("     -> Twist / release the emergency stop button.")
    if not (power_missing or door_open or estop_active):
        print(" [!] FIRMWARE REJECTED MOTION / MOTORS LOCKED:")
        print(f"     Last Error:     '{inst.TheError}'")
        print(f"     Last Exception: '{inst.TheException}'")
        print(f"     Control Error:  {inst.Control.ErrorCode}")
        print(f"     GetErrors:      '{inst.GetErrors()}'")
        print("     -> Power cycle the robot: Turn OFF the power switch on the robot for 10 seconds, then turn it back ON.")

print("=" * 70)

try:
    inst.Dispose()
except Exception:
    pass
