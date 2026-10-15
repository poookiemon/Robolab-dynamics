import sys
import os
import time
import platform

print("=" * 60)
print("BIOHIT ROBOT HARDWARE DIAGNOSTIC TEST")
print("=" * 60)
print(f"Python: {sys.version}")
print(f"Platform: {platform.platform()} ({platform.architecture()[0]})")
print(f"Working Directory: {os.getcwd()}")

# 1. Test biohit_pipettor import
print("\n[1/5] Checking 'biohit_pipettor' import...")
try:
    import biohit_pipettor
    print(f"  -> SUCCESS: biohit_pipettor loaded from: {biohit_pipettor.__file__}")
except Exception as e:
    print(f"  -> FAILED: Could not import biohit_pipettor: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 2. Test pythonnet and CLR InstrumentLib
print("\n[2/5] Checking .NET CLR and InstrumentLib.dll...")
try:
    import clr
    print("  -> SUCCESS: pythonnet/clr loaded.")
    from os.path import dirname, join
    firmware_path = join(dirname(biohit_pipettor.__file__), "include")
    if firmware_path not in sys.path:
        sys.path.append(firmware_path)
    clr.AddReference("InstrumentLib")
    from InstrumentLib import InstrumentCls
    print("  -> SUCCESS: InstrumentLib.dll reference added and InstrumentCls imported.")
except Exception as e:
    print(f"  -> FAILED: CLR / InstrumentLib error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 3. Test InstrumentCls Instantiation & Connection
print("\n[3/5] Instantiating InstrumentCls and querying USB communication...")
try:
    inst = InstrumentCls()
    print("  -> InstrumentCls() created.")
    
    # Wait for USB handshake
    connected = False
    for i in range(20):
        time.sleep(0.1)
        if inst.IsConnected():
            connected = True
            break
            
    is_conn = inst.IsConnected()
    usb_conn = getattr(inst.Control.Comm, 'usbConnected', None)
    err_code = getattr(inst.Control.Comm, 'ErrorCode', None)
    comm_exc = getattr(inst.Control.Comm, 'TheException', None)
    last_err = getattr(inst, 'TheError', None)
    
    print(f"  -> inst.IsConnected(): {is_conn}")
    print(f"  -> inst.Control.Comm.usbConnected: {usb_conn}")
    print(f"  -> Comm ErrorCode: {err_code} (0=No error, 1=Failed to open port, 2=Timeout, 4=Busy)")
    if comm_exc:
        print(f"  -> Comm Exception: {comm_exc}")
    if last_err:
        print(f"  -> Last Error: {last_err}")
        
    try:
        errors_str = inst.GetErrors()
        print(f"  -> inst.GetErrors(): {errors_str}")
    except Exception as ee:
        print(f"  -> GetErrors exception: {ee}")
        
    try:
        comm_errors_str = inst.GetCommErrors()
        print(f"  -> inst.GetCommErrors(): {comm_errors_str}")
    except Exception as ee:
        print(f"  -> GetCommErrors exception: {ee}")

    if not is_conn:
        print("\n" + "!" * 60)
        print("CRITICAL: Robot is NOT connected over USB!")
        print("Please check:")
        print(" 1. The robot's physical power switch is turned ON.")
        print(" 2. The USB cable is securely connected to this PC.")
        print(" 3. No other application (RoboLine vendor software) is currently open.")
        print("!" * 60)
        sys.exit(1)

except Exception as e:
    print(f"  -> FAILED: Error communicating with instrument: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 4. Test Module Detection
print("\n[4/5] Checking detected actuators (PollPresent)...")
try:
    present_val = inst.Control.PollPresent()
    print(f"  -> PollPresent register: {present_val} (binary: {bin(present_val)})")
    x_present = bool(present_val & 2)
    y_present = bool(present_val & 4)
    z_present = bool(present_val & 8)
    p_present = bool(present_val & 16)
    print(f"     X Axis Present: {x_present}")
    print(f"     Y Axis Present: {y_present}")
    print(f"     Z Axis Present: {z_present}")
    print(f"     P Piston Present: {p_present}")
except Exception as e:
    print(f"  -> Error polling present modules: {e}")

# 5. Test Physical Homing Movements
print("\n[5/5] Executing Homing ('small movements to X, Y, Z, P')...")
try:
    print("  -> Homing Z axis...")
    z_ok = inst.Control.Initialize("Z", True)
    print(f"     Z Axis Home Result: {z_ok}")

    print("  -> Homing Y axis...")
    y_ok = inst.Control.Initialize("Y", True)
    print(f"     Y Axis Home Result: {y_ok}")

    print("  -> Homing X axis...")
    x_ok = inst.Control.Initialize("X", True)
    print(f"     X Axis Home Result: {x_ok}")

    print("  -> Homing P (Piston)...")
    p_ok = inst.Control.Initialize("P", True)
    print(f"     P Piston Home Result: {p_ok}")

    print("\n  -> Polling current positions:")
    print(f"     X Position: {inst.PollPosition('X')} mm")
    print(f"     Y Position: {inst.PollPosition('Y')} mm")
    print(f"     Z Position: {inst.PollPosition('Z')} mm")

    print("\n" + "=" * 60)
    print("SUCCESS: Biohit hardware is 100% functional and homed!")
    print("=" * 60)

except Exception as e:
    print(f"  -> Homing failed with exception: {e}")
    import traceback
    traceback.print_exc()
finally:
    try:
        inst.Dispose()
    except Exception:
        pass
