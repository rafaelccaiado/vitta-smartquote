import os
import base64
import json
from google.oauth2 import service_account
from google.oauth2 import credentials

def get_gcp_credentials():
    """
    Retorna credenciais do Google Cloud a partir de variável de ambiente BASE64.
    Suporta tanto Service Account (recomendado) quanto Authorized User (para testes).
    
    Espera env var: GCP_SA_KEY_BASE64
    """
    encoded_key = os.getenv("GCP_SA_KEY_BASE64")
    
    if not encoded_key:
        return None
        
    try:
        decoded_bytes = base64.b64decode(encoded_key)
        info = json.loads(decoded_bytes)
        
        # Verifica o tipo de credencial
        cred_type = info.get("type")
        
        if cred_type == "authorized_user":
            print("⚠️ Usando credenciais de USUÁRIO (Teste apenas).")
            # Credenciais de usuário (local gcloud login)
            creds = credentials.Credentials.from_authorized_user_info(info)
        else:
            print("🔑 Usando credenciais de CONTA DE SERVIÇO (Produção).")
            # Credenciais de serviço (padrão)
            creds = service_account.Credentials.from_service_account_info(info)
            
        return creds
        
    except Exception as e:
        print(f"⚠️ Erro ao carregar credenciais da ENV VAR: {e}")
        return None
