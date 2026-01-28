import requests
import os

# Caminho da imagem (uma das que o usuário enviou)
IMAGE_PATH = r"C:/Users/rafae/.gemini/antigravity/brain/92778fc1-5d28-41a2-a6ac-d0856d1a1855/uploaded_media_1_1769527620916.png"
API_URL = "http://localhost:8000/api/ocr"

def test_ocr():
    if not os.path.exists(IMAGE_PATH):
        print(f"Erro: Imagem não encontrada em {IMAGE_PATH}")
        return

    print(f"Enviando imagem: {IMAGE_PATH}...")
    
    try:
        with open(IMAGE_PATH, "rb") as f:
            files = {"file": f}
            response = requests.post(API_URL, files=files)
            
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("Sucesso! Salvando JSON...")
            import json
            with open("last_ocr_response.json", "w", encoding="utf-8") as f:
                json.dump(response.json(), f, indent=2, ensure_ascii=False)
            print("JSON salvo em last_ocr_response.json")
        else:
            print("Falha:")
            print(response.text)
            
    except Exception as e:
        print(f"Erro na requisição: {e}")

if __name__ == "__main__":
    test_ocr()
