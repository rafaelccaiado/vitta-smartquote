from bigquery_client import BigQueryClient

bq = BigQueryClient()
unit = "Plano Piloto"

all_exams = bq.get_all_exams(unit)

# Buscar TODOS os termos que contenham "funcional"
print("=== FUNCIONAL ===")
count = 0
for e in all_exams:
    if "funcional" in e['search_name']:
        print(f"  {e['search_name']}")
        count += 1

print(f"\nTotal: {count} exames com 'funcional'")

# Buscar termos com "fecal"
print("\n=== FECAL ===")
count = 0
for e in all_exams:
    if "fecal" in e['search_name'] or "fezes" in e['search_name']:
        print(f"  {e['search_name']}")
        count += 1

print(f"\nTotal: {count} exames com 'fecal/fezes'")
