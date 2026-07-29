"""Run the full ETL pipeline end to end: extract -> clean -> dimensions ->
fact -> load -> validate. Each step is a standalone module and can also be run
on its own.
"""
import importlib
import sys

STEPS = [
    "01_extract", "02_clean_split", "03_build_dimensions",
    "04_build_fact", "06_place_authority", "07_code_authority",
    "09_person_authority", "10_place_mentions",
    "05_load_sqlite", "validate",
]


def main():
    for name in STEPS:
        print(f"\n=== {name} ===")
        mod = importlib.import_module(name)
        try:
            mod.main()
        except SystemExit as e:  # validate.py exits non-zero on failure
            if e.code:
                sys.exit(e.code)


if __name__ == "__main__":
    main()
