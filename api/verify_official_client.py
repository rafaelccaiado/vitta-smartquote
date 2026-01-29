from huggingface_hub import InferenceClient
import os

token = os.getenv("HF_TOKEN")
client = InferenceClient(token=token)

models = [
    "microsoft/trocr-base-handwritten",
    "microsoft/trocr-small-handwritten",
    "chinmays18/medical-prescription-ocr",
    "nlpconnect/vit-gpt2-image-captioning"
]

image_path = "C:/Users/rafae/.gemini/antigravity/brain/92778fc1-5d28-41a2-a6ac-d0856d1a1855/uploaded_media_1_1769527620916.png"

print("Testando via InferenceClient...")

with open("client_verification_results.txt", "w") as f:
    for model in models:
        msg = f"\nTestando {model}..."
        print(msg)
        f.write(msg + "\n")
        try:
           # image_to_text call
           result = client.image_to_text(image_path, model=model)
           res_msg = f"SUCESSO: {result}"
           print(res_msg)
           f.write(res_msg + "\n")
        except Exception as e:
           err_msg = f"FALHA: {e}"
           print(err_msg)
           f.write(err_msg + "\n")
