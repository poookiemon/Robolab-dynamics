import winreg

name="FOC_OUTFILE"
value="ss"

print(f"reset Environment Variable {name} to >{value}<")

hkey = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment")
print(f"del Environment Variable {name}")
del hkey

#winreg.SetValueEx(hkey, name, 0, winreg.REG_SZ, value)
#winreg.CloseKey(hkey)
