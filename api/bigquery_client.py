from google.auth.transport.requests import AuthorizedSession
from typing import List, Dict, Any
from auth_utils import get_gcp_credentials
import logging

class BigQueryClient:
    def __init__(self):
        print("Inicializando BigQuery REST Client (Lightweight)...")
        self.project_id = "high-nature-319701"
        self.dataset_id = "vtntprod_vitta_core"
        self.table_id = "lista_precos"
        
        try:
            creds = get_gcp_credentials()
            # Escopo necessário para Query
            if creds.requires_scopes:
                creds = creds.with_scopes(["https://www.googleapis.com/auth/bigquery"])
            
            self.session = AuthorizedSession(creds)
            self.base_url = f"https://bigquery.googleapis.com/bigquery/v2/projects/{self.project_id}/queries"
            print("✅ BQ REST Client Autenticado!")
        except Exception as e:
            print(f"❌ Erro BQ Auth: {e}")
            self.session = None

    def _run_query(self, query: str, parameters: List[Dict] = None) -> List[Dict]:
        """Executa query via REST API e retorna Rows processadas"""
        if not self.session:
            return []
            
        payload = {
            "query": query,
            "useLegacySql": False,
            "parameterMode": "NAMED",
            "queryParameters": parameters or []
        }
        
        try:
            resp = self.session.post(self.base_url, json=payload)
            if resp.status_code != 200:
                print(f"BQ Error {resp.status_code}: {resp.text}")
                return []
                
            data = resp.json()
            rows = data.get("rows", [])
            schema = data.get("schema", {}).get("fields", [])
            
            # Map results to Dict based on Schema
            results = []
            for row in rows:
                item = {}
                values = row.get("f", [])
                for i, field in enumerate(schema):
                    field_name = field.get("name")
                    val = values[i].get("v")
                    item[field_name] = val
                results.append(item)
            return results
            
        except Exception as e:
            print(f"BQ Exception: {e}")
            return []

    def get_all_exams(self, unit: str) -> List[Dict[str, Any]]:
        query = f"""
        SELECT item_id, item_name, group_name, price 
        FROM `{self.project_id}.{self.dataset_id}.{self.table_id}`
        WHERE LOWER(TRIM(price_table_name)) = LOWER(TRIM(@unit))
          AND group_name = 'EXAMES LABORATORIAIS'
        """
        params = [
            {"name": "unit", "parameterType": {"type": "STRING"}, "parameterValue": {"value": unit}}
        ]
        
        raw_results = self._run_query(query, params)
        
        # Post-processing (Normalization compatible with old client)
        processed = []
        for row in raw_results:
            clean_name = row.get("item_name", "").lower()
            for suffix in [" exames laboratoriais", " - exames laboratoriais", " (laboratorio)", " - laboratorio"]:
                if clean_name.endswith(suffix):
                    clean_name = clean_name.replace(suffix, "")
            
            processed.append({
                "item_id": row.get("item_id"),
                "item_name": row.get("item_name"),
                "search_name": clean_name.strip(" -"),
                "group_name": row.get("group_name"),
                "price": row.get("price")
            })
        print(f"Cache BigQuery carregado: {len(processed)} itens para '{unit}'")
        return processed

    def search_exams(self, term: str, unit: str, limit: int = 10) -> List[Dict[str, Any]]:
        query = f"""
        SELECT item_id, item_name, group_name, price 
        FROM `{self.project_id}.{self.dataset_id}.{self.table_id}`
        WHERE LOWER(item_name) LIKE LOWER(@term)
          AND price_table_name = @unit
          AND group_name = 'EXAMES LABORATORIAIS'
        LIMIT @limit
        """
        params = [
            {"name": "term", "parameterType": {"type": "STRING"}, "parameterValue": {"value": f"%{term}%"}},
            {"name": "unit", "parameterType": {"type": "STRING"}, "parameterValue": {"value": unit}},
            {"name": "limit", "parameterType": {"type": "INT64"}, "parameterValue": {"value": str(limit)}}
        ]
        
        return self._run_query(query, params)

    def get_units(self) -> List[str]:
        query = f"""
        SELECT DISTINCT price_table_name
        FROM `{self.project_id}.{self.dataset_id}.{self.table_id}`
        ORDER BY price_table_name
        """
        results = self._run_query(query)
        # Flatten distinct list
        return [r.get("price_table_name") for r in results if r.get("price_table_name")]
