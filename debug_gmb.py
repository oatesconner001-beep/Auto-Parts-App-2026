#!/usr/bin/env python3
"""Debug GMB sheet processing to find eligible rows."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from excel_handler import load_workbook

print("Loading Excel file...")
wb = load_workbook("FISHER SKP INTERCHANGE 20260302.xlsx", read_only=True)
sheet = wb['GMB']

print("Checking GMB rows...")
gmb_rows = 0
eligible_rows = 0
blank_parts = 0

for row_idx, row in enumerate(sheet.iter_rows(min_row=2), start=2):
    if row_idx > 50:  # Check first 50 rows
        break

    gmb_rows += 1

    # Check columns: B=CURRENT SUPPLIER, C=PART #, F=SKP PART #, J=MATCH RESULT
    row_len = len(row)
    supplier = str(row[1].value).strip() if row_len > 1 and row[1].value else ""
    part_num = str(row[2].value).strip() if row_len > 2 and row[2].value else ""
    skp_part = str(row[5].value).strip() if row_len > 5 and row[5].value else ""
    match_result = str(row[9].value).strip() if row_len > 9 and row[9].value else ""

    # Check if this is a GMB row
    if supplier == "GMB":
        # Check if parts are not blank
        if part_num and skp_part and part_num not in ['n/a', '-', '0', 'none', 'tbd', '?'] and skp_part not in ['n/a', '-', '0', 'none', 'tbd', '?']:
            # Check if not already processed
            if not match_result or match_result in ['', 'None']:
                eligible_rows += 1
                print(f"Row {row_idx}: GMB {part_num} vs SKP {skp_part} - ELIGIBLE")

                if eligible_rows >= 5:  # Stop after finding 5
                    break
        else:
            blank_parts += 1

print(f"\nGMB Summary (first 50 rows):")
print(f"  GMB rows found: {gmb_rows}")
print(f"  Eligible for processing: {eligible_rows}")
print(f"  Blank parts: {blank_parts}")

wb.close()