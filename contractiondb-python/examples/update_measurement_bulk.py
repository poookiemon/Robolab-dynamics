
import json
import os
import re
import sys

#sys.path.append("E:\\Labhub\\Repos\\meyerti\\contractiondb-python")

from .contractiondb import ContractionDB
from .contractiondb import CSV_REGEX

from .contractiondb import parse_args


args=parse_args()

args.path=r"S:\MOLP\PHA_LabHub\labhub\devices\HZPHW-FOC4807\2025"

bForce=False

loginData=json.load(open(args.config))
db = ContractionDB(**loginData)


if not os.path.isdir(args.path):
    raise Exception(f"Second Argument does not contain a Directory, {args.path}")
    
for root, dirs, files  in os.walk(args.path, topdown=False):
    for name in files:
        if re.fullmatch(CSV_REGEX, name):
           fname=os.path.join(root, name)           
           try: 
               db.upload_measurement_from_xml(fname, bForce)
               print(f"UPLOAD: {fname}")
           except:
               print(f"ERROR: Skipping {fname}")



db.close()




exit()

