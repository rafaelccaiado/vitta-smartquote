from bigquery_client import BigQueryClient

bq = BigQueryClient()
unit = "Plano Piloto"

all_exams = bq.get_all_exams(unit)


print("\n=== LIVER ENZYMES (TGO/TGP) ===")
targets = ["tgo", "tgp", "ast", "alt", "aminotransferase", "aspartato", "alanina", "litio"]
for e in all_exams:
    found = False
    for t in targets:
        if t in e['search_name']:
            found = True
            break
    
    if found:
        print(f"  MATCH [{t}]:")
        print(f"  search_name: '{e['search_name']}'")
        print(f"  item_name: '{e['item_name']}'")
        print("-" * 20)
