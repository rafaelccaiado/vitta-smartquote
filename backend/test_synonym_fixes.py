import sys
import json
from validation_logic import ValidationService
from bigquery_client import BigQueryClient

# Teste dos termos problemáticos
test_terms = [
    "Coprologico funcional",
    "Pesquisa antígeno fecal para H.pylori",
    "Perfil lipídico"
]

unit = "Plano Piloto"

print(f"Testando correcoes de sinonimos ({unit})...")
print()

bq_client = BigQueryClient()
results = ValidationService.validate_batch(test_terms, unit, bq_client)

for item in results['items']:
    term = item['original_term']
    status = item['status']
    strategy = item.get('match_strategy', 'N/A')
    
    print(f"Termo: {term}")
    print(f"Status: {status}")
    print(f"Estrategia: {strategy}")
    
    if item['matches']:
        print(f"Match: {item['matches'][0]['item_name']}")
    else:
        print(f"Sem match")
    print("-" * 50)

print()
print(f"Resumo:")
print(f"Confirmados: {results['stats']['confirmed']}")
print(f"Pendentes: {results['stats']['pending']}")
print(f"Nao encontrados: {results['stats']['not_found']}")
