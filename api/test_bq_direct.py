from bigquery_client import BigQueryClient

bq = BigQueryClient()
target = "Plano Piloto"

print(f"Target Unit: '{target}' (Len: {len(target)})")

print("Buscando unidades no banco...")
units = bq.get_units()

found = False
for u in units:
    print(f"DEBUG: {repr(u)}")
    if target in u:
        found = True

if found:
    print("Tentando get_all_exams com match exato...")
    exams = bq.get_all_exams(target)
    print(f"Exames retornados: {len(exams)}")
else:
    print("Unidade não encontrada na lista de get_units()!")
