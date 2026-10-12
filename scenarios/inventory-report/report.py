import csv
from pathlib import Path

project_dir = Path(__file__).resolve().parent
input_file = project_dir / "data" / "items.csv"

with input_file.open(newline="", encoding="utf-8") as file:
    rows = list(csv.DictReader(file))

total_quantity = sum(int(row["quantity"]) for row in rows)

print(f"Records: {len(rows)}")
print(f"Total quantity: {total_quantity}")