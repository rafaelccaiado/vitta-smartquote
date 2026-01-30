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

for item in results['items']:
    print(f"\n{'='*60}")
    print(f"Termo: {item['original_term']}")
    print(f"Status: {item['status']}")
    print(f"Estrategia: {item.get('match_strategy', 'N/A')}")
    print(f"\nMatches encontrados ({len(item['matches'])}):")
    
    for i, match in enumerate(item['matches'], 1):
        print(f"  {i}. {match['item_name']} (ID: {match['item_id']}) - R$ {match['price']}")
