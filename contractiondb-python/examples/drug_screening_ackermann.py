import json
import sys
import matplotlib.pyplot as plt
from datetime import datetime
from collections import defaultdict
import numpy as np
import seaborn as sns


#sys.path.append("C:\\Labhub\\Repos\\smartlab\\src")
from src.contractiondb.regex import parse_args
from src.contractiondb import ContractionDB, get_credentials
from src.contractiondb.trace import Trace


args = parse_args()
json_config_path = args.config


with open(json_config_path, 'r') as f:
    config = json.load(f)


args = parse_args()
print(f"config is {args.config}")

loginData = json.load(open(args.config))
db = ContractionDB(**loginData)

start_date = datetime(2024, 12, 10)
end_date = datetime(2024, 12, 14)

# Plate and experiment details for 20241024a
plate_name = '20241024a'
compounds = ["compound1", "compound6"]
concentrations = [0.1, 0.33, 1, 3.33, 10]  # µM
wells_by_compound = {
    "compound1": ['A2', 'B2', 'C2', 'D2',  # 0.1µM replicates
                  'A3', 'B3', 'C3', 'D3',  # 0.33µM replicates
                  'A4', 'B4', 'C4', 'D4',  # 1µM replicates
                  'A5', 'B5', 'C5', 'D5',  # 3.33µM replicates
                  'A6', 'B6', 'C6', 'D6'],  # 10µM replicates
    "compound6": ['E2', 'F2', 'G2', 'H2',  # 0.1µM replicates
                  'E3', 'F3', 'G3', 'H3',  # 0.33µM replicates
                  'E4', 'F4', 'G4', 'H4',  # 1µM replicates
                  'E5', 'F5', 'G5', 'H5',  # 3.33µM replicates
                  'E6', 'F6', 'G6', 'H6']  # 10µM replicates
}

try:
    # Fetch traces for the specific experiment and date range
    traces = db.get_traces(exp=plate_name, start_date=start_date.strftime('%Y-%m-%d'),
                           end_date=end_date.strftime('%Y-%m-%d'))
    print(f"Number of traces fetched: {len(traces)}")

    # Aggregate peak heights by well and measurement date
    well_data = defaultdict(list)  # (measurement_date, peak_height) pairs per well

    for trace in traces:
        if trace.timestamp and start_date <= trace.timestamp <= end_date:
            trace.find_peaks()
            for peak in trace.peaks:
                peak_height = abs(peak.height)
                if peak_height <= 20:  # Filter out peak heights exceeding 20
                    well_data[trace.well].append((trace.timestamp, peak_height))
                    print(
                        f"Row data: well={trace.well}, measurement={trace.name}, peak_height={peak_height}, date={trace.timestamp.strftime('%Y-%m-%d')}")
                else:
                    print(f"Excluding well {trace.well}, measurement {trace.name}: peak height = {peak_height} > 20")
        else:
            print(
                f"Excluding trace for well {trace.well}, measurement {trace.name}: Date {trace.timestamp.strftime('%Y-%m-%d')} outside range {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")

    # Aggregate average peak heights by concentration for each compound
    compound_data = {compound: defaultdict(lambda: defaultdict(list)) for compound in compounds}
    for compound, wells in wells_by_compound.items():
        for i in range(0, len(wells), 4):  # group by concentration
            conc_wells = wells[i:i + 4]
            conc = concentrations[i // 4]
            for well in conc_wells:
                if well_data[well]:
                    for date, height in well_data[well]:
                        compound_data[compound][conc][date].append(height)

    import pandas as pd
    import matplotlib.pyplot as plt

    for compound in compounds:
        rows = []
        for conc, date_dict in compound_data[compound].items():
            for date, heights in date_dict.items():
                for h in heights:
                    rows.append({
                        "concentration": conc,
                        "date": pd.to_datetime(date),
                        "peak_height": h
                    })

        df = pd.DataFrame(rows)
        if df.empty:
            print(f"No data to plot for {compound}")
            continue

        concentrations_sorted = sorted(df['concentration'].unique())
        dates_sorted = sorted(df['date'].unique())
        palette = sns.color_palette("tab10", n_colors=len(concentrations_sorted))

        fig, ax = plt.subplots(figsize=(14, 6))

        width = 0.12  # width of each box
        offset_range = np.linspace(-width * 2, width * 2, len(concentrations_sorted))

        # Plot boxplots for each concentration with x-offsets
        for i, conc in enumerate(concentrations_sorted):
            color = palette[i]
            medians = []
            for j, date in enumerate(dates_sorted):
                data = df[(df['concentration'] == conc) & (df['date'] == date)]['peak_height']
                if len(data) == 0:
                    continue
                ax.boxplot(data,
                           positions=[j + offset_range[i]],
                           widths=width,
                           patch_artist=True,
                           boxprops=dict(facecolor=color, alpha=0.4),
                           medianprops=dict(color='black'),
                           showfliers=False)
                # Scatter points
                ax.scatter([j + offset_range[i]] * len(data), data, color=color, alpha=0.5, s=10)

                # Store median for line plot
                medians.append((j + offset_range[i], np.median(data)))

            # Line connecting medians
            if medians:
                x_vals, y_vals = zip(*medians)
                ax.plot(x_vals, y_vals, color=color, marker='o', label=f"{conc} µM", linewidth=2)


        ax.set_xticks(range(len(dates_sorted)))
        ax.set_xticklabels([d.strftime('%m-%d') for d in dates_sorted])
        ax.set_title(f"Peak Heights for {compound} Over Time (Plate {plate_name})")
        ax.set_xlabel("Date")
        ax.set_ylabel("Peak Height")
        ax.legend(title="Concentration", bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.tight_layout()
        plt.savefig(f"plot_{compound}_final_combined.png")
        plt.close(fig)



except Exception as e:
    print(f"Error occurred: {e}")


db.close()