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
    # SIMPLIFIED V30 LOGIC: CRASH IF FAILS
    decoded_bytes = base64.b64decode(encoded_key)
    info = json.loads(decoded_bytes) # This WILL raise exception if invalid JSON

    # Verifica o tipo de credencial
    cred_type = info.get("type")
    
    if cred_type == "authorized_user":
        creds = credentials.Credentials.from_authorized_user_info(info)
    else:
        creds = service_account.Credentials.from_service_account_info(info)
        
    return creds
