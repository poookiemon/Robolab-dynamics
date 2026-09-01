#from contractiondb import ContractionDB, get_credentials
import json
import os
import sys
import winreg
import re

#sys.path.append("E:\\Labhub\\Repos\\meyerti\\contractiondb-python")

from ..src.contractiondb import ContractionDB
from ..src.contractiondb import parse_args


args = parse_args()
print(f"config is {args.config}")



file_list=[]

if args.files:
    file_list=args.files
else:
    # Öffnen Sie den Registry-Ordner
    reg_key = "FOC_OUTFILE"
    hkey = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment")
    # Lesen Sie die Umgebungsvariable
    fname, type = winreg.QueryValueEx(hkey, reg_key)
    # Drucken Sie den Wert der Umgebungsvariable
    # the FOC_OUTFILE contains the path to xml file, if it is passed auto-convert to csv

    if os.path.isfile(fname):
        file_list.append(fname)
    else:
        print(f"Env {reg_key} does not contain a valid filename >{fname}<")


try:
    loginData = json.load(open(args.config))
    db = ContractionDB(**loginData)
except:
    raise Exception(f"Failed to connect to DB, check Config File >{args.config}<")





print("DONE")



for fname in file_list:

    if re.search(r".xml$", fname):
        fname = re.sub(r"\.xml$", ".csv", fname)
        print(f"fname became {fname}")

    if os.path.isfile(fname):
        print(f"loading  {fname}")
        try:
            print(f"loading  {fname}")
        except:
            raise Exception(f"Second Argument does not contain a valid CSV File, {fname}")


db.commit()












db.close()


print("DONE")

exit()

