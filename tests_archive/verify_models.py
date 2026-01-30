import requests
import os
import json

# Token fixo ou do ambiente
token = os.getenv("HF_TOKEN")
headers = {"Authorization": f"Bearer {token}"}
api_base = "https://api-inference.huggingface.co/models/"

models = [
    "microsoft/trocr-base-handwritten",
    "microsoft/trocr-small-handwritten",
    "microsoft/trocr-large-handwritten",
    "chinmays18/medical-prescription-ocr",
    "nlpconnect/vit-gpt2-image-captioning", 
    "Salesforce/blip-image-captioning-base",
    "facebook/detr-resnet-50"
]

print(f"Testando modelos com token: {token[:4]}...")

with open("verification_results.txt", "w") as f:
    for m in models:
        msg = f"\nTestando {m}..."
        print(msg)
        f.write(msg + "\n")
        
        url = f"{api_base}{m}"
        try:
            image_path = "C:/Users/rafae/.gemini/antigravity/brain/92778fc1-5d28-41a2-a6ac-d0856d1a1855/uploaded_media_1_1769527620916.png"
            with open(image_path, "rb") as img:
                data = img.read()
            
            response = requests.post(url, headers=headers, data=data) 
            
            status_msg = f"Status: {response.status_code}"
            print(status_msg)
            f.write(status_msg + "\n")
            
            if response.status_code != 200:
                error_msg = f"Erro: {response.text[:200]}"
                print(error_msg)
                f.write(error_msg + "\n")
            else:
                f.write("Sucesso!\n")
                
        except Exception as e:
             err = f"Exception: {e}"
             print(err)
             f.write(err + "\n")
