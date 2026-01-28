import os
import base64
import json
from google.oauth2 import service_account

def get_gcp_credentials():
    """
    Retorna credenciais do Google Cloud a partir de variável de ambiente BASE64.
    Ideal para deploy em Vercel/Heroku onde não é seguro subir arquivo JSON.
    
    Espera env var: GCP_SA_KEY_BASE64
    """
    encoded_key = os.getenv("GCP_SA_KEY_BASE64")
    
    if not encoded_key:
        # Retorna None para fallback para estratégia padrão (arquivo local ou gcloud auth)
        return None
        
    try:
        # Decodifica Base64
        decoded_bytes = base64.b64decode(encoded_key)
        service_account_info = json.loads(decoded_bytes)
        
        # Cria objeto de credenciais
        creds = service_account.Credentials.from_service_account_info(service_account_info)
        print("🔑 Credenciais GCP carregadas via ENV VAR (Base64)")
        return creds
        
    except Exception as e:
        print(f"⚠️ Erro ao carregar credenciais da ENV VAR: {e}")
        return None
