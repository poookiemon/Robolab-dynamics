import json
import mysql.connector
import pandas as pd

# Load database info from the JSON file
with open(r"C:\labhub\import\contractiondb2_gwdg.json", "r") as file:
    db_config = json.load(file)

# Connect to the database
try:
    conn = mysql.connector.connect(
        host=db_config["host"],
        port=db_config["port"],
        database=db_config["database"],
        user=db_config["user"],
        password=db_config["password"]
    )

    print("✅ Connected to the database!")

    # Run a test query
    cursor = conn.cursor()
    cursor.execute("SHOW TABLES")
    tables = [row[0] for row in cursor.fetchall()]

    print(f"\n📋 Found {len(tables)} tables:\n - " + "\n - ".join(tables))

    excel_filename = "full_database_export.xlsx"
    with pd.ExcelWriter(excel_filename, engine='openpyxl') as writer:
        for table in tables:
            print(f"📥 Exporting '{table}' to Excel sheet...")
            try:
                # Read the whole table into a pandas DataFrame
                df = pd.read_sql(f"SELECT * FROM {table}", conn)
                # Write to a sheet named after the table
                df.to_excel(writer, sheet_name=table[:31], index=False)  # Excel sheet names max length = 31
            except Exception as table_err:
                print(f"⚠️ Could not export table '{table}': {table_err}")

    print(f"\n✅ Exported all tables to '{excel_filename}'")

    cursor.close()
    conn.close()
    print("🔌 Connection closed.")

except mysql.connector.Error as err:
    print(f"❌ Database error: {err}")
except Exception as e:
    print(f"❌ Unexpected error: {e}")