import json
import sys
from matplotlib import pyplot as plt

sys.path.append(r"E:\Labhub\Repos\meyerti\contractiondb-python\src")

from src.contractiondb import ContractionDB
from src.contractiondb import parse_args

args=parse_args()

print(f"config is {args.config}")

loginData=json.load(open(args.config))
db = ContractionDB(**loginData)

traces = db.get_trace_ids(args.expName, args.meaName, args.wellName)

input(f"Will analyze {len(traces)} matching {args.expName} {args.meaName} {args.wellName}")

#fig, axs = plt.subplots()

# plot them
for t in traces:
    try:
        db.add_trace(t)
        if t.time is None:
            print(f"ERROR: trace {t} has no time")
            continue
        t.filter_min_max()
        peak = t.find_peaks()

        if len(peak) > 100:
            print(f"In {t.name} are {len(peak)} peaks, skip")
            continue

        #t.plot(fig,axs)
        db.remove_peaks_from_trace(t)
        db.add_peaks_to_trace(t)
        print(f"UPLOAD: {t.name}")
        db.commit()
    except:
        print(f"ERROR: Skipping {t.name} {t.well}")

print('done')
