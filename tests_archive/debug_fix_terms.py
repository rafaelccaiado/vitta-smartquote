from bigquery_client import BigQueryClient
import json

bq = BigQueryClient()
unit = "Plano Piloto" # Unidade padrao

terms_to_debug = [
    "coprologico", 
    "funcional", 
    "pylori", 
    "antigeno", 
    "fecal", 
    "lipidograma"
]

print(f"--- Debugging Valid Terms in BigQuery ({unit}) ---")
all_exams = bq.get_all_exams(unit)

found = {}
for term in terms_to_debug:
    found[term] = []
    for e in all_exams:
        if term in e['search_name']:
            found[term].append(e['search_name'])

print(json.dumps(found, indent=2, ensure_ascii=False))
