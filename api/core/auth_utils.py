import os
import base64
import json
from google.oauth2 import service_account
from google.oauth2 import credentials

def get_gcp_credentials():
    encoded_key = os.getenv("GCP_SA_KEY_BASE64")
    
    if not encoded_key:
        key_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gcp_key.json")
        if os.path.exists(key_path):
            return service_account.Credentials.from_service_account_file(key_path)
        raise ValueError("Env Var GCP_SA_KEY_BASE64 Missing and gcp_key.json not found!")
    
    decoded_bytes = base64.b64decode(encoded_key)
    try:
        raw_str = decoded_bytes.decode('utf-8', errors='ignore')
        clean_str = raw_str.replace('\\r', '').replace('\\n', ' ').replace('\n', ' ').replace('\r', '').strip()
        
        # Safe Parse
        import ast
        try:
             info = ast.literal_eval(clean_str)
        except:
             info = json.loads(clean_str)
             
        if "private_key" in info:
             raw_key = info["private_key"]
             if not ("\n" in raw_key and not "\\n" in raw_key):
                 import re
                 body = raw_key.replace("-----BEGIN PRIVATE KEY-----", "").replace("-----END PRIVATE KEY-----", "")
                 body = re.sub(r'[\s\\]+', '', body)
                 chunked_body = '\n'.join(body[i:i+64] for i in range(0, len(body), 64))
                 info["private_key"] = f"-----BEGIN PRIVATE KEY-----\n{chunked_body}\n-----END PRIVATE KEY-----\n"

    except Exception as e:
         raise ValueError(f"CRITICAL: Auth Mapper failed. Error: {e}")

    cred_type = info.get("type")
    if cred_type == "authorized_user":
        creds = credentials.Credentials.from_authorized_user_info(info)
    else:
        creds = service_account.Credentials.from_service_account_info(info)
        
    return creds
