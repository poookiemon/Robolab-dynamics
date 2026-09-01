import matplotlib.pyplot as plt


import sys
sys.path.append("C:\Labhub\Repos\contractiondb-python")

from src.contractiondb import ContractionDB, get_credentials

# open database connection

database, port, host = "contractionDb2", "3307", "mysqldb-unigoe.gwdg.de"


#cred = 'C:\\labhub\\import\\contractiondb.json'
cred = 'C:\\labhub\\import\\smartlab_db_gwdg.json'


username, password = get_credentials()
db = ContractionDB(host=host, port=port, database=database, user=username, password=password)


# download measurements (all filters are optional)
measurements = db.get_measurements(well="A1", start_date="2022-01-01", end_date="2022-12-31",
                                   measurement_suffix="_stim0")

# plot them
for m in measurements:
    plt.plot(m.time, m.raw_distance, "-k")
    plt.title(f"Plate {m.plate}, Well {m.well}\nMeasurement {m.name}")
    plt.xlabel("Time / s")
    plt.ylabel("Raw distance / pixel")
    plt.show()

