from google.auth.transport.requests import AuthorizedSession
from typing import List, Dict, Any
from core.auth_utils import get_gcp_credentials
import logging

class BigQueryClient:
    def __init__(self):
        print("Initializing BigQuery REST Client (Lightweight)...")
        self.project_id = "high-nature-131701"
        self.dataset_id = "rtnt_prod_vitta_core"
        self.table_id = "lista_precos"
        
        try:
            creds = get_gcp_credentials()
            
            # Scopes for Query
            if creds.requires_scopes:
                creds = creds.with_scopes(['https://www.googleapis.com/auth/cloud-platform'])
            
            self.session = AuthorizedSession(creds)
            self.base_url = f"https://bigquery.googleapis.com/bigquery/v2/projects/{self.project_id}/queries"
            self.auth_info = "OK"
            print("🛡️ BQ REST Client Authenticated!")
        except Exception as e:
            self.auth_info = f"ERR: {str(e)[:50]}"
            print(f"❌ Error BQ Auth: {e}")
            self.session = None

    def _run_query(self, query: str, parameters: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Executa query via REST API e retorna Rows processadas"""
        if not self.session:
            return []
            
        # V106: Strictly sanitized payload to avoid BQ_ERR_400
        payload = {
            "query": query,
            "useLegacySql": False
        }
        
        if parameters:
            payload["queryParameters"] = parameters
            payload["parameterMode"] = "NAMED"
        
        try:
            resp = self.session.post(self.base_url, json=payload)
            if resp.status_code != 200:
                # Capture accurate error info for V106 probe
                try:
                    full_err = resp.json().get("error", {}).get("message", resp.text[:100])
                except:
                    full_err = resp.text[:100]
                
                self.auth_info = f"BQ_ERR_{resp.status_code}: {full_err[:80]}"
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
                    
                    # Type Casting (REST API returns strings)
                    if field_name == "price" and val is not None:
                        try:
                            val = float(val)
                        except:
                            val = 0.0
                    
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
        """
        params = [
            {"name": "unit", "parameterType": {"type": "STRING"}, "parameterValue": {"value": unit}}
        ]
        
        raw_results = self._run_query(query, params)

        if not raw_results:
            print(f"⚠️ 0 results for '{unit}'. Attempting BLIND FETCH (Catalog Discovery)...")
            query_blind = f"""
            SELECT item_id, item_name, group_name, price 
            FROM `{self.project_id}.{self.dataset_id}.{self.table_id}`
            LIMIT 500
            """
            raw_results = self._run_query(query_blind)
            if raw_results:
                self.auth_info = f"OK (BLIND MODE)"
        
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
        print(f"Cache BigQuery Carregado: {len(processed)} itens para '{unit}'")
        return processed

    def search_exams(self, term: str, unit: str, limit: int = 10) -> List[Dict[str, Any]]:
        query = f"""
        SELECT item_id, item_name, group_name, price 
        FROM `{self.project_id}.{self.dataset_id}.{self.table_id}`
        WHERE LOWER(item_name) LIKE LOWER(@term)
        AND LOWER(TRIM(price_table_name)) = LOWER(TRIM(@unit))
        LIMIT @limit
        """
        params = [
            {"name": "term", "parameterType": {"type": "STRING"}, "parameterValue": {"value": f"%{term}%"}},
            {"name": "unit", "parameterType": {"type": "STRING"}, "parameterValue": {"value": unit}},
            {"name": "limit", "parameterType": {"type": "INT64"}, "parameterValue": {"value": str(limit)}}
        ]
        
        return self._run_query(query, params)

    def get_raw_table_stats(self) -> Dict[str, Any]:
        """Diagnostic: Counts rows and gets top units."""
        query = f"SELECT count(*) as total FROM `{self.project_id}.{self.dataset_id}.{self.table_id}`"
        res = self._run_query(query)
        total = res[0].get("total", 0) if res else 0
        
        query_units = f"SELECT price_table_name, count(*) as c FROM `{self.project_id}.{self.dataset_id}.{self.table_id}` GROUP BY price_table_name LIMIT 5"
        units_res = self._run_query(query_units)
        units_str = "|".join([str(u.get("price_table_name")) for u in units_res])
        
        return {"total": total, "sample_units": units_str}

    def get_units(self) -> List[str]:
        query = f"""
        SELECT DISTINCT price_table_name
        FROM `{self.project_id}.{self.dataset_id}.{self.table_id}`
        ORDER BY price_table_name
        """
        results = self._run_query(query)
        # Flatten distinct list
        return [r.get("price_table_name") for r in results if r.get("price_table_name")]

# Singleton
bq_client = BigQueryClient()
