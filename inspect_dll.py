import clr
import os
import sys

dll_path = os.path.abspath("InstrumentLib.dll")
if not os.path.exists(dll_path):
    dll_path = os.path.abspath("instrumentLib.dll")

if not os.path.exists(dll_path):
    print("Cannot find InstrumentLib.dll")
    sys.exit(1)

clr.AddReference(dll_path)
import System

print("--- ALL Classes found in the DLL ---")
found = False
for assembly in System.AppDomain.CurrentDomain.GetAssemblies():
    name = assembly.FullName.lower()
    # Skip standard Microsoft/System libraries to avoid clutter
    if "mscorlib" in name or "system" in name or "python" in name:
        continue
        
    print(f"\nAssembly: {assembly.FullName}")
    for type_info in assembly.GetTypes():
        print(f"  -> {type_info.FullName}")
        found = True

if not found:
    print("Literally no classes found. Is this a native C++ DLL instead of a C# .NET DLL?")
