import matplotlib.pyplot as plt
import numpy as np

import json
import numpy as np
import sys

sys.path.append("E:\\Labhub\\Repos\\meyerti\\contractiondb-python")

from src.contractiondb import ContractionDB
from src.contractiondb.csv_utils import read_measurements_from_csv

config_filename = "c:\Labhub\Import\contractiondb2_gwdg.json"
#config_filename = "c:\Labhub\Import\smartlab_db_gwdg.json"
loginData=json.load(open(config_filename))

db = ContractionDB(**loginData)
print(sys.argv)


# download measurements (all filters are optional)
#measurements = db.get_measurements(well="A1", start_date="2022-01-01", end_date="2022-12-31", measurement_suffix="_stim0")

measurements = db.get_measurements(well="A1")


#measurements = db.get_measurements(well="A1",)

# plot them
for m in measurements:
    if m.raw_distance==None :
        print(f"No data for {m.plate} {m.name} {m.well}")
        continue
    plt.plot(m.time, m.raw_distance, "-k")
    plt.title(f"Plate {m.plate}, Well {m.well}\nMeasurement {m.name} {m.id}")
    plt.xlabel("Time / s")
    plt.ylabel("Raw distance / pixel")
    plt.show()


print('done')
