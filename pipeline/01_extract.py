"""Step 1 — Extract.

Read the source .xls with xlrd (pure Python) and dump a verbatim UTF-8 CSV,
one row per source data-row, tagged with source_row. The empty 15th column
(index 14) is dropped.
"""
import csv

import xlrd

from common import RAW_CSV, RAW_HEADERS, XLS_PATH, ensure_dirs, render_cell


def main():
    ensure_dirs()
    book = xlrd.open_workbook(XLS_PATH)
    sheet = book.sheet_by_index(0)

    # Row 0 is the header; data rows start at index 1. Keep source columns
    # 0..13; column 14 is empty.
    kept_cols = list(range(14))

    written = 0
    with open(RAW_CSV, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(RAW_HEADERS)
        for r in range(1, sheet.nrows):
            values = [render_cell(sheet.cell_value(r, c)) for c in kept_cols]
            if not any(v.strip() for v in values):
                continue  # skip fully-blank rows (defensive; none expected)
            w.writerow([r] + values)
            written += 1

    print(f"Extracted {written} data rows -> {RAW_CSV}")


if __name__ == "__main__":
    main()
