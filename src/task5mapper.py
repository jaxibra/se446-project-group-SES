#!/usr/bin/env python3
import sys

# Index of relevant columns (check your CSV header!)
# Schema: ID, Case Number, Date, ..., Arrest(8), ..., District(11)
ARREST_IDX = 8

for line in sys.stdin:
    line = line.strip()

    # Skip empty lines
    if not line:
        continue

    parts = line.split(',')

    # Sanity Check: Ensure line has enough columns
    if len(parts) <= ARREST_IDX:
        continue

    # Extract fields
    arrest_status = parts[ARREST_IDX].lower() # 'true' or 'false'

    # LOGIC: Only emit if it IS an arrest
    if arrest_status == 'true':
        # Emit (Key=District, Value=1)
        print(f"Arrested\t1")
    else:
        print("Not Arrested\t1")