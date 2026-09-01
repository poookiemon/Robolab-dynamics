import mysql.connector
import pandas as pd
import matplotlib.pyplot as plt


# MySQL connection setup
conn = mysql.connector.connect(
    host='maxscale.mysql.gwdg.de',      
    user='labhub',
    password='Q50i59Izs',
    database='3307'
)

cursor = conn.cursor()

# Get distinct x.name values (e.g. different experiments)
cursor.execute("""
    SELECT DISTINCT x.name
    FROM experiment x
""")
experiment_names = [row[0] for row in cursor.fetchall()]

# Query template
query_template = """
    SELECT x.name AS experiment, m.name AS measurement, l.name AS labware, 
           e.date, ROUND(AVG(peak.height), 2) AS avg_peak_height
    FROM peak
    JOIN forces USING(idEvent)
    JOIN event e USING(idEvent)
    JOIN labware l USING(idLabware)
    JOIN measurement m ON e.idParent = m.idEvent
    JOIN event em ON m.idEvent = em.idEvent
    JOIN experiment x ON em.idParent = x.idEvent
    WHERE x.name = %s AND l.name = 'B2'
    GROUP BY e.date
"""

all_data = []

# Fetch and combine data for all experiments
for exp_name in experiment_names:
    cursor.execute(query_template, (exp_name,))
    data = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    df = pd.DataFrame(data, columns=columns)
    all_data.append(df)

cursor.close()
conn.close()

# Combine into one DataFrame
df_all = pd.concat(all_data, ignore_index=True)
df_all['date'] = pd.to_datetime(df_all['date'], errors='coerce')

# Plot each experiment's data

plt.figure(figsize=(12, 6))
for key, grp in df_all.groupby("experiment"):
    plt.plot(grp['date'], grp['avg_peak_height'], marker='o', label=key)

plt.title("Average Peak Height Over Time")
plt.xlabel("Date")
plt.ylabel("Average Peak Height")
plt.legend(title="Experiment")
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()
