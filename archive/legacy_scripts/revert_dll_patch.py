import re

with open('Biohit-Automated-Pipettor-GUI/working.py', 'r') as f:
    code = f.read()

old_block = """try:
    import clr
    import os
    import sys
    
    # Check for the raw DLL file
    dll_path = os.path.abspath("instrumentLib.dll")
    if os.path.exists(dll_path):
        # Load the DLL directly via its absolute path
        clr.AddReference(dll_path)
        print("SUCCESS: Loaded instrumentLib.dll via pythonnet.")
        
        # Import the Pipettor class (assuming the namespace matches the old wrapper or is global)
        try:
            from biohit_pipettor import Pipettor as RealBiohitPipettor
        except ImportError:
            try:
                from InstrumentLib import Pipettor as RealBiohitPipettor
            except ImportError:
                # Fallback: search the loaded assemblies for anything named Pipettor
                import System
                RealBiohitPipettor = None
                for assembly in System.AppDomain.CurrentDomain.GetAssemblies():
                    for type_info in assembly.GetTypes():
                        if type_info.Name == "Pipettor":
                            RealBiohitPipettor = type_info
                            break
                    if RealBiohitPipettor: break
                if not RealBiohitPipettor:
                    raise ImportError("Could not find 'Pipettor' class inside instrumentLib.dll")
                    
        HAS_BIOHIT_DLL = True
        print("SUCCESS: Hardware Bridge Established via instrumentLib.dll")
    else:
        # Fallback to standard python package import if dll isn't present
        from biohit_pipettor import Pipettor as RealBiohitPipettor
        HAS_BIOHIT_DLL = True
        print("SUCCESS: Hardware Bridge Established via native biohit_pipettor package.")
        
except Exception as e:
    HAS_BIOHIT_DLL = False
    print(f"CRITICAL: Bridge failed. Ensure 'instrumentLib.dll' is in the root folder. Error: {e}")
    RealBiohitPipettor = None"""

new_block = """import traceback
try:
    from biohit_pipettor import Pipettor as RealBiohitPipettor
    HAS_BIOHIT_DLL = True
    print("SUCCESS: Hardware Bridge Established via native biohit_pipettor package.")
except Exception as e:
    HAS_BIOHIT_DLL = False
    print(f"CRITICAL: Bridge failed. Ensure 'biohit_pipettor' is installed. Error: {e}")
    traceback.print_exc()
    RealBiohitPipettor = None"""

if old_block in code:
    code = code.replace(old_block, new_block)
    with open('Biohit-Automated-Pipettor-GUI/working.py', 'w') as f:
        f.write(code)
    print("REVERT SUCCESSFUL")
else:
    print("FAILED TO MATCH")
