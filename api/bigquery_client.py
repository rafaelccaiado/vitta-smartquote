try:
    from google.cloud import bigquery
except ImportError:
    bigquery = None
from typing import List, Dict, Any
from auth_utils import get_gcp_credentials

class BigQueryClient:
    def __init__(self):
        if not bigquery:
            print("⚠️ BigQuery lib not installed. BQ features disabled.")
            self.client = None
            return

        creds = get_gcp_credentials()
        if creds:
             self.client = bigquery.Client(project="high-nature-319701", credentials=creds)
        else:
             self.client = bigquery.Client(project="high-nature-319701")
             
        self.project_id = "high-nature-319701"
        self.dataset_id = "vtntprod_vitta_core"
        self.table_id = "lista_precos"

    def get_all_exams(self, unit: str) -> List[Dict[str, Any]]:
        """Busca TODOS os exames da unidade para cache em memória (Otimização de Performance)"""
        if not self.client:
             print("⚠️ BigQuery Client offline. Retornando Mock vazio.")
             return []

        query = f"""
        SELECT 
            item_id, 
            item_name, 
            group_name, 
            price 
        FROM `{self.project_id}.{self.dataset_id}.{self.table_id}`
        WHERE LOWER(TRIM(price_table_name)) = LOWER(TRIM(@unit))
          AND group_name = 'EXAMES LABORATORIAIS'
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("unit", "STRING", unit),
            ]
        )

        try:
            query_job = self.client.query(query, job_config=job_config)
            results = []
            for row in query_job:
                # Normaliza nome para busca (remove sufixos comuns de tabelas)
                clean_name = row.item_name.lower()
                for suffix in [" exames laboratoriais", " - exames laboratoriais", " (laboratorio)", " - laboratorio"]:
                    if clean_name.endswith(suffix):
                        clean_name = clean_name.replace(suffix, "")
                
                clean_name = clean_name.strip(" -")
                
                results.append({
                    "item_id": row.item_id,
                    "item_name": row.item_name, # Manter original para display
                    "search_name": clean_name.strip(), # Limpo para match exato
                    "group_name": row.group_name,
                    "price": row.price
                })
            print(f"Cache BigQuery carregado: {len(results)} itens para unidade '{unit}'")
            return results
        except Exception as e:
            print(f"Erro no BigQuery: {e}")
            return []

    def search_exams(self, term: str, unit: str, limit: int = 10) -> List[Dict[str, Any]]:
        if not self.client:
             return []

        # Legacy: Mantido para retrocompatibilidade, mas lento para loops
        query = f"""
        SELECT 
            item_id, 
            item_name, 
            group_name, 
            price 
        FROM `{self.project_id}.{self.dataset_id}.{self.table_id}`
        WHERE LOWER(item_name) LIKE LOWER(@term)
          AND price_table_name = @unit
          AND group_name = 'EXAMES LABORATORIAIS'
        LIMIT @limit
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("term", "STRING", f"%{term}%"),
                bigquery.ScalarQueryParameter("unit", "STRING", unit),
                bigquery.ScalarQueryParameter("limit", "INTEGER", limit),
            ]
        )

        query_job = self.client.query(query, job_config=job_config)
        results = []
        for row in query_job:
            results.append({
                "item_id": row.item_id,
                "item_name": row.item_name,
                "group_name": row.group_name,
                "price": row.price
            })
        
        return results

    def get_units(self) -> List[str]:
        if not self.client:
            # Fallback List
            return [
                "Goiânia Centro", 
                "Anápolis", 
                "Trindade", 
                "Aparecida de Goiânia", 
                "Rio Verde", 
                "Jataí", 
                "Catalão"
            ]

        query = f"""
        SELECT DISTINCT price_table_name
        FROM `{self.project_id}.{self.dataset_id}.{self.table_id}`
        ORDER BY price_table_name
        """
        query_job = self.client.query(query)
        return [row.price_table_name for row in query_job]
