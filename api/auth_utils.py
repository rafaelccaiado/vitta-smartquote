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
    
    # FINAL SANITIZER V36: Fix PEM Private Key
    try:
        raw_str = decoded_bytes.decode('utf-8', errors='ignore')
        
        # Clean up whitespace noise for JSON structure
        # Substitui \\r e \\n por espaços para garantir que o JSON parse funcione
        clean_str = raw_str.replace('\\r', '').replace('\\n', ' ').replace('\n', ' ').replace('\r', '').strip()
        
        import ast
        try:
             info = ast.literal_eval(clean_str)
        except:
             info = json.loads(clean_str)
             
        # FIX DEEP: Corrigir a chave privada que precisa de quebras de linha REAIS
        if "private_key" in info:
             # Se a chave privada veio com \\n literais, converte para \n reais
             info["private_key"] = info["private_key"].replace("\\n", "\n")
             
    except Exception as e:
         raise ValueError(f"CRITICAL: Final Sanitizer failed. Raw preview: {raw_str[:30]}... Error: {e}")

    # Verifica o tipo de credencial
    cred_type = info.get("type")
    
    if cred_type == "authorized_user":
        creds = credentials.Credentials.from_authorized_user_info(info)
    else:
        creds = service_account.Credentials.from_service_account_info(info)
        
    return creds
