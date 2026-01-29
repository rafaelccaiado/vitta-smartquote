import requests
import json
import os

# Caminho da imagem de teste (ORIGINAL)
image_path = "C:/Users/rafae/.gemini/antigravity/brain/92778fc1-5d28-41a2-a6ac-d0856d1a1855/pedido_medico_teste_1769524367458.png"

url = "http://127.0.0.1:8000/api/ocr"

if not os.path.exists(image_path):
    # Fallback ou erro
    print(f"Imagem nova não achada, tentando a antiga")
    image_path = "C:/Users/rafae/.gemini/antigravity/brain/92778fc1-5d28-41a2-a6ac-d0856d1a1855/pedido_medico_teste_1769524367458.png"

print(f"Enviando POST para {url} com imagem {os.path.basename(image_path)}...")

try:
    with open(image_path, "rb") as f:
        files = {"file": f}
        response = requests.post(url, files=files)
    
    print(f"Status Code: {response.status_code}")
    
    try:
        data = response.json()
        with open("last_response.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        print("\n--- RESPOSTA API (JSON) ---")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        
        print("\n--- ANALISE DEBUG ---")
        debug = data.get("debug_raw", [])
        for step in debug:
            print(f"Model: {step.get('model')}")
            if "error" in step:
                print(f"  ❌ ERROR: {step.get('error')}")
            if "text" in step:
                print(f"  ✅ TEXT: {step.get('text')[:100]}...") # Truncar
                
    except json.JSONDecodeError:
        print("Erro ao decodificar JSON")
        print(response.text)

except Exception as e:
    print(f"Erro na requisição: {e}")
