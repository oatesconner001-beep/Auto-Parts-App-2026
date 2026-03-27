#!/usr/bin/env python3
"""Debug script to check UNCERTAIN rows in Anchor sheet."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from excel_handler import load_workbook

print("Loading Excel file...")
wb = load_workbook("FISHER SKP INTERCHANGE 20260302.xlsx", read_only=True)
sheet = wb['Anchor']

print("Checking UNCERTAIN rows...")
uncertain_count = 0
total_rows = 0

for row_idx, row in enumerate(sheet.iter_rows(min_row=2), start=2):
    if row_idx > 1000:  # Check first 1000 rows
        break

    total_rows += 1

    # Check columns: B=CURRENT SUPPLIER, J=MATCH RESULT
    supplier = str(row[1].value).strip() if row[1].value else ""
    match_result = str(row[9].value).strip() if row[9].value else ""
    part_num = str(row[2].value).strip() if row[2].value else ""
    skp_part = str(row[5].value).strip() if row[5].value else ""

    if supplier == "ANCHOR" and match_result == "UNCERTAIN":
        uncertain_count += 1
        print(f"Row {row_idx}: ANCHOR {part_num} vs SKP {skp_part} = UNCERTAIN")

        if uncertain_count >= 10:  # Stop after finding 10
            break

print(f"\nFound {uncertain_count} UNCERTAIN rows in first {total_rows} rows")
wb.close()