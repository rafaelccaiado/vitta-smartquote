from bigquery_client import BigQueryClient
import unicodedata

def normalize(text):
    return unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('ASCII').lower().strip()

bq = BigQueryClient()
unit = "Plano Piloto"
all_exams = bq.get_all_exams(unit)

targets = ["tgo", "tgp", "ast", "alt", "aspartato", "alanina", "litio"]

print(f"Total exams: {len(all_exams)}")
for e in all_exams:
    s_name = e['search_name']
    for t in targets:
        if t in s_name:
            print(f"[{t.upper()}] Found: '{s_name}' -> ID: {e.get('id', '?')}")
