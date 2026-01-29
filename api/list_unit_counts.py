from bigquery_client import BigQueryClient
from google.cloud import bigquery

bq = BigQueryClient()
print("Contando exames por unidade...")

query = f"""
SELECT price_table_name, COUNT(*) as total
FROM `{bq.project_id}.{bq.dataset_id}.{bq.table_id}`
WHERE group_name = 'EXAMES LABORATORIAIS' AND price_table_name LIKE '%LIGGI%'
GROUP BY price_table_name
ORDER BY total DESC
LIMIT 20
"""

query_job = bq.client.query(query)
results = list(query_job)
if not results:
    print("Nenhuma tabela LIGGI encontrada. Buscando TOP 5 gerais:")
    query = f"""
    SELECT price_table_name, COUNT(*) as total
    FROM `{bq.project_id}.{bq.dataset_id}.{bq.table_id}`
    WHERE group_name = 'EXAMES LABORATORIAIS'
    GROUP BY price_table_name
    ORDER BY total DESC
    LIMIT 5
    """
    query_job = bq.client.query(query)

for row in query_job:
    print(f"UNIT: '{row.price_table_name}' | TOTAL: {row.total}")
