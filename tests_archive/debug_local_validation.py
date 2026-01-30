from validation_logic import ValidationService
from bigquery_client import BigQueryClient
import json
import sys

# Encoding fix for Windows console
sys.stdout.reconfigure(encoding='utf-8')

unit = "Plano Piloto"
terms = ["EAS"]

print(f"Testing validation for terms: {terms} in unit: {unit}")

bq = BigQueryClient()
# validation_logic usa metodos estaticos, entao funciona direto
res = ValidationService.validate_batch(terms, unit, bq)

print("\n--- RESULT ---")
print(json.dumps(res, indent=2, ensure_ascii=False, default=str))

print("\n--- DUMPING KEYS TO JSON ---")
all_exams = bq.get_all_exams(unit)
keys = []
for e in all_exams:
    sn = e['search_name']
    if "urina" in sn or "eas" in sn or "rotina" in sn:
        keys.append(sn)

with open("exam_keys.json", "w", encoding="utf-8") as f:
    json.dump(keys, f, ensure_ascii=False, indent=2)
print("Keys dumped to exam_keys.json")
