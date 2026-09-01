
#from contractiondb import ContractionDB, get_credentials
import json
import numpy as np
import sys


import pandas as pd

sys.path.append("E:\Labhub\Repos\meyerti\contractiondb-python")


from src.contractiondb import ContractionDB
from src.contractiondb.csv_utils import read_measurements_from_csv

config_filename = "c:\Labhub\Import\contractiondb2_gwdg.json"
loginData=json.load(open(config_filename))
db = ContractionDB(**loginData)

##
#define input

fname="E:\\Documents\\People\\chanut_emma\\autoOrgan_stage1_all_E18.CSV"
expName='20240110a_E18_wt_Drug3'
plateType='384_well_MTP'


df = pd.read_csv(fname)



id_exp=db.register_experiment(expName, plateType)


print(id_exp)

print(sys.argv)


id_plate =db.get_id_plate(expName) 

if db.plate_has_wells(id_plate)==0:
    db.plate_add_wells(id_plate)

wells = db.get_id_wells(id_plate)




id_mea =db.get_id_measurement(expName, meaName)
if id_mea==0:
    id_mea = db.add_measurement(expName, meaName)

id_event_type =db.get_id_eventtype('measurement')

## then we can load the data

#data = np.loadtxt(fname, delimiter=",", dtype=float)
#time = data[:, 0]
#time -= time[0]

measurements = read_measurements_from_csv(fname, expName, meaName)


# upload forces
for m in measurements:
    id=db.add_forces(id_mea, m.well)
    db.updateRawDistance(id, m.raw_distance)
                         


db.close()

