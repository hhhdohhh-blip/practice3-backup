import random
from pathlib import Path

root = Path("company_data")

departments = ["insurance", "claims", "buh"]

for dept in departments:
    (root / dept).mkdir(parents=True, exist_ok=True)

    for i in range(1, 7):
        lines = [
            f"{dept};doc{i};{random.randint(1000, 99999)}"
            for _ in range(200)
        ]

        file_path = root / dept / f"report_{i}.csv"
        file_path.write_text("\n".join(lines), encoding="utf-8")

print("Тестовые данные созданы!")
