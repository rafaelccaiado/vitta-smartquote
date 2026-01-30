import time
from ocr_processor import OCRProcessor
import os

processor = OCRProcessor()
image_path = "C:/Users/rafae/.gemini/antigravity/brain/92778fc1-5d28-41a2-a6ac-d0856d1a1855/pedido_medico_teste_1769524367458.png"

with open(image_path, "rb") as f:
    img_bytes = f.read()

print("\n--- TESTE DE VELOCIDADE EASYOCR (CPU) ---")
start = time.time()
text_easy = processor._process_easyocr(img_bytes)
end = time.time()
print(f"Tempo EasyOCR: {end - start:.2f}s")
print(f"Texto (First 50): {text_easy[:50]}...")

from PIL import Image
import io

# ... (código anterior)

print("\n--- TESTE DE VELOCIDADE DONUT (CPU + QUANTIZED) ---")
start = time.time()
image = Image.open(io.BytesIO(img_bytes)).convert("RGB")
text_donut = processor._process_hf_local(image, "medical")
end = time.time()
print(f"Tempo Donut: {end - start:.2f}s")
