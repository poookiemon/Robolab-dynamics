import json
import sys

sys.path.append("C:\Labhub\Repos\contractiondb-python")

from src.contractiondb import ContractionDB
config_filename = "c:\Labhub\Import\smartlab_db_gwdg.json"
loginData=json.load(open(config_filename))
db = ContractionDB(**loginData)

# do something with the database
wells = db.get_id_wells(313)
experiments=db.get_experiments()


print('Got ' + str(len(experiments)) + ' Experiments')


# Step 1: Look up the experiment's idEvent
id_exp_event = next((e.id for e in experiments if e.name == "20241024a"), None)

print("Selected experiment ID:", id_exp_event)


# Step 2: Only call get_id_measurement if we found a matching id
if id_exp_event:
    id_measurement = db.get_id_measurement(exp=id_exp_event, mea="B2")
    print("Measurement ID:", id_measurement)
    if id_measurement:
        print("Measurement found:", id_measurement)
    else:
        print("Measurement not found for that experiment/well.")
else:
    print("Experiment not found.")
