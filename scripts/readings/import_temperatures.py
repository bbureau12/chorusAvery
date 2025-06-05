import pandas as pd
import sqlite3
import os
import glob

# Configuration
data_folder = "readings/temperature"
db_path = "db/chorusAvery.db"
print(f"Absolute Path: {os.path.abspath(db_path)}")

# Connect to the database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Loop through each .csv file
for filepath in glob.glob(os.path.join(data_folder, "*.csv")):
    print(f"\nProcessing file: {filepath}")

    # Prompt user for LocationID
    location_id_input = input(f"Enter LocationID for file '{os.path.basename(filepath)}': ")

    try:
        location_id = int(location_id_input)
    except ValueError:
        print("Invalid input. LocationID must be an integer. Skipping this file.")
        continue

    try:
        # Find the header row index
        with open(filepath, 'r') as f:
            lines = f.readlines()

        header_index = next(
            (i for i, line in enumerate(lines) if 'Date,Time,Deg C,Deg F' in line),
            None
        )

        if header_index is None:
            print(f"Error: Header row not found in file {filepath}. Skipping this file.")
            continue

        # Read the CSV starting from the header row
        df = pd.read_csv(filepath, skiprows=header_index)

        # Strip column names (in case of extra spaces)
        df.columns = df.columns.str.strip()

        # Combine Date and Time columns into DateTime_UTC
        df['DateTime_UTC'] = pd.to_datetime(df['Date'] + ' ' + df['Time'], format='%m/%d/%Y %H:%M:%S')

        # Keep only DateTime_UTC and Deg F columns
        df = df[['DateTime_UTC', 'Deg F']]

        # Rename columns to match schema
        df.rename(columns={
            'Deg F': 'Temp_F'
        }, inplace=True)

        # Round Temp_F and cast to int
        df['Temp_F'] = df['Temp_F'].round().astype(int)

        # Add LocationID
        df['LocationID'] = location_id

        # Reorder columns
        df = df[['LocationID', 'DateTime_UTC', 'Temp_F']]

        # Print each row
        for _, row in df.iterrows():
            print(f"Importing: LocationID={row['LocationID']}, DateTime_UTC={row['DateTime_UTC']}, Temp_F={row['Temp_F']}")

        # Append to database
        df.to_sql("Location_Temperature", conn, if_exists="append", index=False)
        conn.commit()

        # Delete the processed file
        os.remove(filepath)
        print(f"Deleted file: {filepath}")

    except Exception as e:
        print(f"Error processing file {filepath}: {e}")

# Close database connection
conn.close()
print("\nImport complete!")
