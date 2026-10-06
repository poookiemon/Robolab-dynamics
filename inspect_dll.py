import clr
import os
import sys

dll_path = os.path.abspath("instrumentLib.dll")
if not os.path.exists(dll_path):
    print("Cannot find instrumentLib.dll")
    sys.exit(1)

clr.AddReference(dll_path)
import System

print("--- Classes found in instrumentLib.dll ---")
found_types = []
for assembly in System.AppDomain.CurrentDomain.GetAssemblies():
    if "instrumentLib" in assembly.FullName:
        for type_info in assembly.GetTypes():
            if type_info.IsPublic:
                found_types.append(type_info.FullName)
                print(type_info.FullName)

if not found_types:
    print("No public classes found! Are you sure this is the right DLL?")
