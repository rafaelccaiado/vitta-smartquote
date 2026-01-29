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
        # Vercel/Local Fallback: Procura arquivo gcp_key.json no diretório da API
        # IMPORTANTE: Apenas se não houver a env var (prioridade para Env Var)
        key_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gcp_key.json")
        if os.path.exists(key_path):
            return service_account.Credentials.from_service_account_file(key_path)
        raise ValueError("Env Var GCP_SA_KEY_BASE64 Missing and gcp_key.json not found!")
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
             
        # FIX DEEP V38: Reconstrução Nuclear da Chave Privada
        if "private_key" in info:
             raw_key = info["private_key"]
             
             # Se já tem quebras reais e parece válido, não toca (pra não estragar o que funciona)
             if "\n" in raw_key and not "\\n" in raw_key:
                 pass
             else:
                 # Limpeza agressiva: Remove cabeçalhos e tudo que não é base64
                 import re
                 # Remove headers
                 body = raw_key.replace("-----BEGIN PRIVATE KEY-----", "").replace("-----END PRIVATE KEY-----", "")
                 # Remove whitespace e backslashes
                 body = re.sub(r'[\s\\]+', '', body)
                 
                 # Reconstroi formato PEM padrão (64 chars por linha)
                 chunked_body = '\n'.join(body[i:i+64] for i in range(0, len(body), 64))
                 
                 info["private_key"] = f"-----BEGIN PRIVATE KEY-----\n{chunked_body}\n-----END PRIVATE KEY-----\n"

    except Exception as e:
         raise ValueError(f"CRITICAL: Final Sanitizer failed. Raw preview: {raw_str[:30]}... Error: {e}")

    # Verifica o tipo de credencial
    cred_type = info.get("type")
    
    if cred_type == "authorized_user":
        creds = credentials.Credentials.from_authorized_user_info(info)
    else:
        creds = service_account.Credentials.from_service_account_info(info)
        
    return creds
