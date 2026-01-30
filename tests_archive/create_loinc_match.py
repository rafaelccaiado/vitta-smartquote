from google.cloud import bigquery

PROJECT_ID = "high-nature-319701"
DATASET_ID = "vtntprod_vitta_core"
SOURCE_TABLE = "loinc_sinonimos"
PRICE_TABLE = "lista_precos"
DEST_TABLE = "loinc_match_precos"

def create_match_table():
    client = bigquery.Client(project=PROJECT_ID)
    
    query = f"""
    CREATE OR REPLACE TABLE `{PROJECT_ID}.{DATASET_ID}.{DEST_TABLE}` AS
    SELECT DISTINCT
        l.loinc_num,
        l.nome_oficial as loinc_nome,
        l.classe as loinc_classe,
        p.item_id,
        p.item_name,
        'exact_synonym' as match_type
    FROM `{PROJECT_ID}.{DATASET_ID}.{SOURCE_TABLE}` l
    JOIN `{PROJECT_ID}.{DATASET_ID}.{PRICE_TABLE}` p
    ON LOWER(TRIM(l.sinonimo)) = LOWER(TRIM(REGEXP_REPLACE(p.item_name, r'(?i)\s*-\s*exames\s+laboratoriais.*', '')))
    WHERE p.group_name = 'EXAMES LABORATORIAIS'
    """
    
    print("🚀 Iniciando processamento de Match no BigQuery...")
    print(f"Query:\n{query}")
    
    job = client.query(query)
    job.result() # Wait
    
    print(f"✅ Tabela {DEST_TABLE} criada com sucesso!")
    
    # Check count
    count_job = client.query(f"SELECT COUNT(*) as total FROM `{PROJECT_ID}.{DATASET_ID}.{DEST_TABLE}`")
    rows = list(count_job)
    print(f"📊 Total de matches encontrados: {rows[0].total}")

if __name__ == "__main__":
    create_match_table()
