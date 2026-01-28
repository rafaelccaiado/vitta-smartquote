import pandas as pd
from google.cloud import bigquery
import os
import glob

# Config
PROJECT_ID = "high-nature-319701"
DATASET_ID = "vtntprod_vitta_core"
TABLE_ID = "loinc_sinonimos"
LOINC_PATH = "../../loinc_data/Loinc.csv"
PT_PATH = "../../loinc_data/ptBR_LinguisticVariant.csv"

# Classes relevantes para Laboratório de Análises Clínicas
RELEVANT_CLASSES = [
    'CHEM',    # Química
    'HEM/BC',  # Hematologia e Contagem de Células
    'SERO',    # Sorologia
    'UA',      # Urinálise
    'COAG',    # Coagulação
    'MICRO',   # Microbiologia
    'TOX',     # Toxicologia
    'ABXBACT', # Antibióticos vs Bactérias
    'CHAL',    # Testes de Desafio (Curvas)
    'CYTO'     # Citologia
]

def run_etl():
    print("🚀 Iniciando ETL LOINC -> BigQuery")
    
    # 1. Carregar LOINC Principal (apenas colunas úteis)
    print("📖 Lendo Loinc.csv...")
    cols_loinc = ['LOINC_NUM', 'COMPONENT', 'RELATEDNAMES2', 'LONG_COMMON_NAME', 'CLASS']
    df_loinc = pd.read_csv(LOINC_PATH, usecols=cols_loinc, dtype=str, low_memory=False)
    
    # Filtrar classes
    print(f"📊 Total LOINC: {len(df_loinc)}")
    df_loinc = df_loinc[df_loinc['CLASS'].isin(RELEVANT_CLASSES)].copy()
    print(f"📉 Filtrado por classes lab: {len(df_loinc)}")
    
    # 2. Carregar Tradução PT-BR
    print("🇧🇷 Lendo ptBR_LinguisticVariant.csv...")
    # O arquivo de tradução geralmente tem colunas: LOINC_NUM, LONG_COMMON_NAME (Em PT)
    # Vamos inspecionar as colunas se der erro, mas o padrão é LOINC_NUM em comum
    try:
        df_pt = pd.read_csv(PT_PATH, dtype=str, low_memory=False)
        # Adaptar nomes se necessário. Geralmente o ptBR tem 'LOINC_NUM' e 'LONG_COMMON_NAME' traduzido
        # Vamos assumir que a coluna de nome traduzido é 'LONG_COMMON_NAME' ou similar.
        # Se o CSV tiver estrutura complexa, ajustaremos.
        # Pelo padrão, muitas vezes é: LOINC_NUM, COMPONENT, PROPERTY...
        # A tradução costuma estar no LONG_COMMON_NAME ou RELATEDNAMES2 desse arquivo
        
        # Estrategia: Manter LOINC_NUM e renomear LONG_COMMON_NAME para NOME_PT
        possible_name_cols = ['LONG_COMMON_NAME', 'LongCommonName', 'EX_US_D', 'LONG_COMMON_NAME_PT']
        name_col_pt = next((c for c in df_pt.columns if c in possible_name_cols), None)
        
        if not name_col_pt:
            # Fallback: tentar pegar a última coluna de texto grande
            name_col_pt = df_pt.columns[-1] 
            print(f"⚠️ Coluna de nome PT não identificada, usando: {name_col_pt}")

        df_pt = df_pt[['LOINC_NUM', name_col_pt]].rename(columns={name_col_pt: 'NOME_PT'})
        
        # Merge
        df_merged = df_loinc.merge(df_pt, on='LOINC_NUM', how='left')
        
        # Preencher nome oficial: Se tem PT usa PT, senão usa EN
        df_merged['nome_oficial'] = df_merged['NOME_PT'].fillna(df_merged['LONG_COMMON_NAME'])
        
    except Exception as e:
        print(f"⚠️ Erro ao carregar tradução (prosseguindo sem PT): {e}")
        df_merged = df_loinc.copy()
        df_merged['nome_oficial'] = df_merged['LONG_COMMON_NAME']

    # 3. processar Sinônimos
    print("dismantling sinônimos...")
    rows = []
    
    # Iterar eficientemente
    for _, row in df_merged.iterrows():
        loinc = row['LOINC_NUM']
        nome = row['nome_oficial']
        classe = row['CLASS']
        
        # Lista base de termos para buscar
        termos = set()
        
        # Adiciona o próprio nome oficial e o nome em inglês
        if pd.notna(nome): termos.add(nome)
        if pd.notna(row['LONG_COMMON_NAME']): termos.add(row['LONG_COMMON_NAME'])
        if pd.notna(row['COMPONENT']): termos.add(row['COMPONENT'])
        
        # Extrai sinônimos do RELATEDNAMES2 (separado por ;)
        rels = str(row['RELATEDNAMES2'])
        if rels and rels.lower() != 'nan':
            parts = [p.strip() for p in rels.split(';') if p.strip()]
            termos.update(parts)
            
        # Gera linhas para tabela final
        for termo in termos:
            if len(termo) < 2: continue # Ignora lixo
            rows.append({
                "loinc_num": loinc,
                "sinonimo": termo.lower(), # Normalizado para busca
                "nome_oficial": nome,
                "classe": classe
            })
            
    df_final = pd.DataFrame(rows)
    print(f"📚 Total de sinônimos gerados: {len(df_final)}")
    
    # 4. Upload para BigQuery
    print("☁️ Enviando para BigQuery...")
    client = bigquery.Client(project=PROJECT_ID)
    table_ref = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"
    
    job_config = bigquery.LoadJobConfig(
        write_disposition="WRITE_TRUNCATE", # Substitui tabela
        schema=[
            bigquery.SchemaField("loinc_num", "STRING"),
            bigquery.SchemaField("sinonimo", "STRING"),
            bigquery.SchemaField("nome_oficial", "STRING"),
            bigquery.SchemaField("classe", "STRING"),
        ]
    )
    
    job = client.load_table_from_dataframe(df_final, table_ref, job_config=job_config)
    job.result() # Aguarda
    
    print(f"✅ Sucesso! Tabela {table_ref} criada com {job.output_rows} linhas.")

if __name__ == "__main__":
    run_etl()
