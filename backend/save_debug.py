import sys
import json
from validation_logic import ValidationService
from bigquery_client import BigQueryClient

# Teste dos termos problemáticos
test_terms = [
    "Coprologico funcional",
    "Pesquisa antígeno fecal para H.pylori"
]

unit = "Plano Piloto"

bq_client = BigQueryClient()
results = ValidationService.validate_batch(test_terms, unit, bq_client)

# Salvar em arquivo
with open("debug_output.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)

print("Resultado salvo em debug_output.json")
