from src.contractiondb import read_measurements_from_csv

import matplotlib.pyplot as plt

measurements = read_measurements_from_csv("../20210401c/20210525a.csv")

# plot them
for m in measurements:
    plt.plot(m.time, m.raw_distance, "-k")
    plt.title(f"Plate {m.plate}, Well {m.well}\nMeasurement {m.name}")
    plt.xlabel("Time / s")
    plt.ylabel("Raw distance / pixel")
    plt.show()
