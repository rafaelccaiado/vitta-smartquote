import os
import base64
import json

def convert_adc_key():
    # Caminho padrão do ADC no Windows
    app_data = os.getenv('APPDATA')
    adc_path = os.path.join(app_data, 'gcloud', 'application_default_credentials.json')
    
    print(f"🔍 Lendo credenciais locais de: {adc_path}")
    
    try:
        with open(adc_path, "rb") as f:
            content = f.read()
            # Verificar se é um JSON válido antes de converter
            json.loads(content)
            
            encoded = base64.b64encode(content).decode("utf-8")
            with open("key_base64.txt", "w") as out:
                out.write(encoded)
            print("✅ Chave salva em key_base64.txt")
            
    except FileNotFoundError:
        print("❌ Arquivo de credenciais não encontrado.")
    except json.JSONDecodeError:
        print("❌ O arquivo não parece ser um JSON válido.")
    except Exception as e:
        print(f"❌ Erro: {e}")

if __name__ == "__main__":
    convert_adc_key()
