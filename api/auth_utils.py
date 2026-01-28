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
    if not encoded_key: raise ValueError("Env Var GCP_SA_KEY_BASE64 Missing!")
    decoded_bytes = base64.b64decode(encoded_key)
    
    # SANITIZER V31: Limpa sujeira da string antes de ler
    try:
        json_str = decoded_bytes.decode('utf-8')
        # Remove quebras de linha e escapes perigosos que podem ter vindo do copy-paste
        json_str = json_str.replace('\r', '').replace('\n', '').strip()
        
        info = json.loads(json_str)
    except Exception as e:
         raise ValueError(f"CRITICAL: Sanitizer failed. Raw: {decoded_bytes[:20]}... Error: {e}")

    # Verifica o tipo de credencial
    cred_type = info.get("type")
    
    if cred_type == "authorized_user":
        creds = credentials.Credentials.from_authorized_user_info(info)
    else:
        creds = service_account.Credentials.from_service_account_info(info)
        
    return creds
