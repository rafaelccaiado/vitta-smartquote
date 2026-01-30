from bigquery_client import BigQueryClient

bq = BigQueryClient()
print("Buscando unidades...")
units = bq.get_units()
print("Unidades disponíveis:")
for u in units:
    print(f"- {u}")
