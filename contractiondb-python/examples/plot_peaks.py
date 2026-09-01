import json
import sys

sys.path.append("C:\Labhub\Repos\contractiondb-python")



import matplotlib.pyplot as plt
from src.contractiondb import ContractionDB

# configfile.json could look like this:
# {
#     "host": "my-mysql-host",
#     "port": 1234,
#     "database": "my-database-name",
#     "user": "my-username",
#     "password": "my-password"
# }

# open database connection
# *args (Non-Keyword Arguments)
# The special syntax *args in function definitions in python is used to pass 
# a variable number of arguments to a function. It is used to pass a non-key 
# worded, variable-length argument list. 

# **kwargs (Keyword Arguments)
# The special syntax **kwargs in function definitions in python is used to pass
#  a keyworded, variable-length argument list. We use the name kwargs with the
#   double star. The reason is because the double star allows us to pass through
#    keyword arguments (and any number of them).

config_filename = "c:\Labhub\Import\contractiondb.json"
loginData=json.load(open(config_filename))
db = ContractionDB(**loginData)

# do something with the database
# db.get_measurements()


# download measurements (all filters are optional)
# measurements = db.get_measurements(plate="20210401c", well="A1", start_date="2021-01-01", end_date="2021-12-31", measurement_suffix="_stim0")

measurements = db.get_measurements(idForces=617)




# plot them
for m in measurements:
    peaks=db.get_peaks_of_measurement(m)
    plt.plot(m.time, m.raw_distance, "-k")
    plt.title(f"Plate {m.plate}, Well {m.well}\nMeasurement {m.name}")
    plt.xlabel("Time / s")
    plt.ylabel("Raw distance / pixel")
    plt.show()

