#!/usr/bin/env python3
import sys

# Index of relevant columns (check your CSV header!)
# Schema: ID, Case Number, Date, ..., Arrest(8), ..., District(11)
date_index = 2

for line in sys.stdin:
    line = line.strip()

    # Skip empty lines
    if not line:
        continue

    parts = line.split(',')

    # Sanity Check: Ensure line has enough columns
    if len(parts) <= date_index:
        continue

    if parts[0] == "ID":
        continue
    # Extract fields
    datetime = parts[date_index].lower() 
    splitter = datetime.split(' ')
    date = splitter[0]
    splitter2 = date.split('/')
    year = splitter2[2]
    print(f"{year}\t1")