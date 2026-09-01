from src.contractiondb import ContractionDB

# Step 1: Connect to the database
db = ContractionDB(
    host="maxscale.mysql.gwdg.de",
    database="contractiondb2",
    user="labhub",
    password="Q50i59Izs",
    port="3307"
)

# Step 2: Fetch traces

data=db.execute_sql("select name from person")

traces = db.get_trace_ids("20241024a", None,  "B2")

# Step 3: Print results
for t in traces:
    print(f"id is {t.id}")
