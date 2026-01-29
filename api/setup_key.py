import base64
import json
import os

def encode_key():
    print("--- GERADOR DE CHAVE GCP PARA VERCEL ---")
    print("1. Cole o conteúdo do seu arquivo JSON do Google abaixo.")
    print("2. Pressione ENTER duas vezes para finalizar.\n")
    
    lines = []
    while True:
        try:
            line = input()
            if not line:
                break
            lines.append(line)
        except EOFError:
            break
            
    content = "\n".join(lines)
    
    try:
        # Validar se é JSON
        json_obj = json.loads(content)
        
        # Converter para bytes e depois base64
        original_bytes = json.dumps(json_obj).encode('utf-8')
        base64_bytes = base64.b64encode(original_bytes)
        base64_string = base64_bytes.decode('utf-8')
        
        print("\n\n✅ SUCESSO! Copie o código abaixo (tudo que está entre as linhas):")
        print("-" * 50)
        print(base64_string)
        print("-" * 50)
        print("\n👉 Vá no Vercel > Settings > Environment Variables")
        print("👉 Crie uma variável chamada: GCP_SA_KEY_BASE64")
        print("👉 Cole o código acima no valor.\n")
        
    except json.JSONDecodeError:
        print("\n❌ ERRO: O texto colado não é um JSON válido. Tente novamente.")
    except Exception as e:
        print(f"\n❌ ERRO: {e}")

if __name__ == "__main__":
    encode_key()
