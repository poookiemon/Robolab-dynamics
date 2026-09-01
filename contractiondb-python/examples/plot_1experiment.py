
import json
import mysql.connector
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime
from collections import defaultdict


# Specify the JSON config file path
json_config_path = "c:\\Labhub\\Import\\contractiondb.json"

# Load JSON configuration
try:
    print(f"Loading JSON config from: {json_config_path}")
    with open(json_config_path, 'r') as f:
        config = json.load(f)
    print("JSON config loaded successfully:", config)
except FileNotFoundError:
    print(f"Error: JSON config file not found at {json_config_path}")
    raise
except json.JSONDecodeError:
    print(f"Error: Invalid JSON format in {json_config_path}")
    raise

# Initialize the database connection
try:
    conn = mysql.connector.connect(**config)
    print("Database connection established successfully")
except mysql.connector.Error as e:
    print(f"Error: Failed to connect to database: {e}")
    raise

# Get data with custom query to include peak heights for all wells
try:
    cursor = conn.cursor(dictionary=True)
    query = """
    SELECT x.name AS experiment, m.name AS measurement, l.name AS well, e.date,
           p.height AS peak_height, e.idEvent
    FROM peak p
    JOIN forces f USING (idEvent)
    JOIN event e USING (idEvent)
    JOIN labware l USING (idLabware)
    JOIN measurement m ON e.idParent = m.idEvent
    JOIN event em ON m.idEvent = em.idEvent
    JOIN experiment x ON em.idParent = x.idEvent
    WHERE x.name = %s
    """
    print(query)
    cursor.execute(query, ("20241024a",))
    rows = cursor.fetchall()
    print(f"Fetched {len(rows)} rows for experiment 20241024a")
except mysql.connector.Error as e:
    print(f"Error: Database query failed: {e}")
    raise
finally:
    cursor.close()
    conn.close()

# Plot all measurements for all wells with separate lines
if not rows:
    print("No data found for experiment 20241024a.")
else:
    # Aggregate peak heights by idEvent and well
    peak_data = defaultdict(lambda: defaultdict(list))
    for row in rows:
        peak_data[row['well']][row['idEvent']].append(row['peak_height'])
        print(f"Row data: well={row['well']}, idEvent={row['idEvent']}, measurement={row['measurement']}, peak_height={row['peak_height']}")

    # Calculate average peak height per idEvent for each well
    all_times = {}
    all_avg_peak_heights = {}
    for well, events in peak_data.items():
        times = []
        avg_peak_heights = []
        exp_date = datetime.strptime("20241024a".replace('a', ''), '%Y%m%d')  # Experiment start date
        for id_event, heights in events.items():
            if heights:
                avg_peak_height = round(np.mean(heights), 2)
                event_row = next((r for r in rows if r['idEvent'] == id_event and r['well'] == well), None)
                if event_row and event_row['measurement']:
                    mea_date_str = event_row['measurement'].replace('a', '')
                    try:
                        mea_date = datetime.strptime(mea_date_str, '%Y%m%d')
                        time_days = (mea_date - exp_date).days
                    except ValueError:
                        print(f"Warning: Invalid measurement date format for well {well}, idEvent {id_event}: {mea_date_str}")
                        continue
                else:
                    print(f"No measurement date found for well {well}, idEvent {id_event}, skipping")
                    continue
                times.append(time_days)
                avg_peak_heights.append(avg_peak_height)
                print(f"Well {well}, Event {id_event}: Avg peak height = {avg_peak_height}, Time = {time_days} days")
        all_times[well] = times
        all_avg_peak_heights[well] = avg_peak_heights

    # Plot with a line for each well
    plt.figure(figsize=(14, 10))
    # Sort wells alphabetically and numerically
    sorted_wells = sorted(all_times.keys(), key=lambda x: (x[0], int(x[1:])))
    colors = {}  # Dictionary to store colors for each well
    # Define base colors for each row

    row_colors = {
        'A': (1.0, 0.0, 0.0, 1.0),  # Red
        'B': (0.0, 0.0, 1.0, 1.0),  # Blue
        'C': (0.0, 1.0, 0.0, 1.0),  # Green
        'D': (0.5, 0.0, 0.5, 1.0),  # Purple
        'E': (1.0, 0.5, 0.0, 1.0),  # Orange
        'F': (1.0, 1.0, 0.0, 1.0),  # Yellow
        'G': (0.0, 1.0, 1.0, 1.0),  # Cyan
        'H': (0.6, 0.3, 0.0, 1.0)   # Brown
    }

    # Assign colors to all possible wells A1-H6, even if no data
    all_possible_wells = [f"{row}{col}" for row in 'ABCDEFGH' for col in range(1, 7)]
    for well in all_possible_wells:
        row = well[0]
        if row in row_colors:
            n_wells = 6  # Fixed number of wells per row (1-6)
            color_values = np.linspace(0.2, 0.8, n_wells)  # Gradient range (light to dark)
            base_color = row_colors[row]
            col_num = int(well[1:])
            gradient_factor = color_values[col_num - 1]  # Index 0-5 for columns 1-6
            # Linear interpolation for gradient
            r = base_color[0] + (1.0 - base_color[0]) * (1.0 - gradient_factor) if base_color[0] > 0 else base_color[0] * gradient_factor
            g = base_color[1] + (1.0 - base_color[1]) * (1.0 - gradient_factor) if base_color[1] > 0 else base_color[1] * gradient_factor
            b = base_color[2] + (1.0 - base_color[2]) * (1.0 - gradient_factor) if base_color[2] > 0 else base_color[2] * gradient_factor
            a = 1.0  # Alpha
            colors[well] = (r, g, b, a)

    # Plot only wells with data
    for i, well in enumerate(sorted_wells):
        if well in all_times:  # Only plot if data exists
            times = all_times[well]
            peak_heights = all_avg_peak_heights[well]
            sorted_indices = np.argsort(times)
            times_sorted = [times[i] for i in sorted_indices]
            peak_heights_sorted = [peak_heights[i] for i in sorted_indices]
            plt.plot(times_sorted, peak_heights_sorted, '-', color=colors[well], label=f"Well {well}", linewidth=2)

    # Add points without value annotations
    for well in sorted_wells:
        if well in all_times:  # Only plot if data exists
            times = all_times[well]
            peak_heights = all_avg_peak_heights[well]
            sorted_indices = np.argsort(times)
            times_sorted = [times[i] for i in sorted_indices]
            peak_heights_sorted = [peak_heights[i] for i in sorted_indices]
            for j, (time, height) in enumerate(zip(times_sorted, peak_heights_sorted)):
                plt.plot(time, height, 'o', color=colors[well])

    plt.title("Measurements for All Wells (Avg Peak Height vs Time)")
    plt.xlabel("Time (Days since Experiment 20241024a)")
    plt.ylabel("Average Peak Height (rounded to 2 decimals)")
    plt.legend(bbox_to_anchor=(1, 1.15), loc='upper left')  # Move legend outside plot
    plt.grid(True)
    plt.draw()
    plt.savefig("all_wells_measurements_line.png")  # Save the plot
    plt.show()  # Display the plot interactively
    print("Plot displayed and saved as all_wells_measurements_line.png")