import json
import os
import re
import sys
from ..src.contractiondb import ContractionDB
from ..src.contractiondb import CSV_REGEX
from ..src.contractiondb import parse_args

force = False
bUpdateTraces = True

bTest = True
args = parse_args()
print(f"config is {args.config}")

loginData = json.load(open(args.config))
db = ContractionDB(**loginData)

root = args.path
force = args.force

if os.path.isdir(root) == False:
    raise Exception(f"Second Argument does not contain a Directory, {root}")
else:
    input(f"Uploading all content starting from {root} force {force}")

for root, dirs, files in os.walk(root, topdown=False):
    for name in files:
        if re.fullmatch(CSV_REGEX, name):
            fname = os.path.join(root, name)
            try:
                if bUpdateTraces:
                    print(f"TEST: would upload {fname}")
                elif bUpdateTraces:
                    db.upload_traces_from_csv(fname, force)
                else:
                    db.upload_measurement_from_csv(fname, force)

            except:
                print(f"ERROR: Skipping {fname}")
                db.close()
                db = ContractionDB(**loginData)

db.close()

print("done")