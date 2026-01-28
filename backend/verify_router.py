import requests
import os
import json

# Token fixo ou do ambiente
token = os.getenv("HF_TOKEN")
headers = {"Authorization": f"Bearer {token}"}

# URL antiga: https://api-inference.huggingface.co/models/
# Nova tentativa: https://router.huggingface.co/hf-inference/models/
# Ou apenas: https://router.huggingface.co/models/

urls_to_test = [
    "https://router.huggingface.co/hf-inference/models/",
    "https://router.huggingface.co/models/"
]

model = "microsoft/trocr-base-handwritten"
image_path = "C:/Users/rafae/.gemini/antigravity/brain/92778fc1-5d28-41a2-a6ac-d0856d1a1855/uploaded_media_1_1769527620916.png"

print(f"Testando nova URL para modelo {model}...")

with open(image_path, "rb") as img:
    data = img.read()

for base in urls_to_test:
    url = f"{base}{model}"
    print(f"\nTentando: {url}")
    try:
        response = requests.post(url, headers=headers, data=data)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            print("SUCESSO! Text:", str(response.json())[:100])
        else:
            print("Falha:", response.text[:200])
    except Exception as e:
        print(f"Erro: {e}")
