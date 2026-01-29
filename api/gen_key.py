import os
import base64
import glob

def find_and_convert_key():
    print("🔍 Procurando arquivo de chave 'high-nature*.json'...")
    
    # Locais para buscar
    search_paths = [
        ".",
        "..",
        "../..",
        "../../..",
        "C:/Users/rafae/Downloads",
        "C:/Users/rafae/OneDrive/Área de Trabalho/Antigravity",
        "C:/Users/rafae/OneDrive/Área de Trabalho/Antigravity/orcamento_vitta"
    ]
    
    found_file = None
    
    for path in search_paths:
        # Busca recursiva simples (apenas 1 nível em cada path listado)
        pattern = os.path.join(path, "high-nature*.json")
        matches = glob.glob(pattern)
        
        # Também busca recursivamente se estiver no Windows (pode ser lento, então limitamos)
        if not matches:
             # Tenta 1 nível abaixo
             pattern = os.path.join(path, "*", "high-nature*.json")
             matches = glob.glob(pattern)
             
        if matches:
            found_file = matches[0]
            break
            
    if found_file:
        print(f"✅ Arquivo encontrado: {os.path.abspath(found_file)}")
        try:
            with open(found_file, "rb") as f:
                encoded = base64.b64encode(f.read()).decode("utf-8")
                print("\n" + "="*80)
                print("🔑 SUA CHAVE BASE64 (Copie TUDO entre as linhas):")
                print("="*80)
                print(encoded)
                print("="*80)
        except Exception as e:
            print(f"❌ Erro ao ler arquivo: {e}")
    else:
        print("❌ Não consegui encontrar o arquivo 'high-nature*.json' automaticamente.")
        print("Por favor, coloque o arquivo JSON na pasta 'backend' e rode o script novamente.")

if __name__ == "__main__":
    find_and_convert_key()
