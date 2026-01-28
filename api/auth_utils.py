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
    
    # SUPER SANITIZER V34: Limpeza em profundidade
    try:
        raw_str = decoded_bytes.decode('utf-8', errors='ignore')
        
        # Estágio 1: Remover escapes literais comuns de copy-paste incorreto
        clean_str = raw_str.replace('\\n', ' ').replace('\\r', '')
        
        # Estágio 2: Remover quebras reais
        clean_str = clean_str.replace('\n', ' ').replace('\r', '')
        
        # Estágio 3: Remover aspas escapadas incorretamente se houver
        # (Não vamos mexer nas aspas por enquanto para não quebrar JSON, focar no whitespace)
        
        clean_str = clean_str.strip()
        
        info = json.loads(clean_str)
    except Exception as e:
         # Se falhar, tenta estratégia de fallback: literal eval se parecer um dict python stringificado
         try:
            import ast
            info = ast.literal_eval(clean_str)
         except:
             raise ValueError(f"CRITICAL: Super Sanitizer failed. Raw preview: {raw_str[:30]}... Error: {e}")

    # Verifica o tipo de credencial
    cred_type = info.get("type")
    
    if cred_type == "authorized_user":
        creds = credentials.Credentials.from_authorized_user_info(info)
    else:
        creds = service_account.Credentials.from_service_account_info(info)
        
    return creds
