"""Generate tiny_catalog.xlsx used by importer tests.

Structure (0-indexed rows):
  Row 0 (header):   Equipamentos | XLT 3.0L V6 AT 26MY
  Row 1 (model):    NaN          | RANGER 26MY
  Row 2 (category): Engine & Transmission | NaN
  Row 3 (attr):     Potência     | 250           ← numeric
  Row 4 (attr):     Tração 4x4 (high/low) | X    ← boolean true

Run:  python tests/importer/fixtures/make_tiny_catalog.py
"""

from pathlib import Path

import pandas as pd


def make() -> None:
    rows = [
        ["Equipamentos", "XLT 3.0L V6 AT 26MY"],
        [None, "RANGER 26MY"],
        ["Engine & Transmission", None],
        ["Potência", 250],
        ["Tração 4x4 (high/low)", "X"],
    ]
    df = pd.DataFrame(rows)
    out = Path(__file__).parent / "tiny_catalog.xlsx"
    df.to_excel(out, index=False, header=False, sheet_name="BASE")
    print(f"Written: {out}")


if __name__ == "__main__":
    make()
