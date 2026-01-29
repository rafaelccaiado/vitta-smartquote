from ocr_processor import OCRProcessor
import os
from PIL import Image
import io

# Path da imagem de teste (a mesma usada anteriormente ou a nova enviada)
image_path = "C:/Users/rafae/.gemini/antigravity/brain/92778fc1-5d28-41a2-a6ac-d0856d1a1855/pedido_medico_teste_1769524367458.png"

print(f"--- INICIANDO DEBUG DE QUALIDADE OCR ---")
print(f"Imagem: {image_path}")

if not os.path.exists(image_path):
    print("Imagem não encontrada!")
    exit()

with open(image_path, "rb") as f:
    image_bytes = f.read()

processor = OCRProcessor()

print("\n\n1. TESTANDO DONUT (Medical)...")
try:
    # Força chamada direta interna para ver erro real
    image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    text_donut = processor._process_hf_local(image, "medical")
    print(f"[DONUT RESULT]:\n'{text_donut}'")
    print(f"Length: {len(text_donut)}")
except Exception as e:
    print(f"[DONUT ERROR]: {e}")
    import traceback
    traceback.print_exc()

print("\n\n2. TESTANDO TROCR (Microsoft)...")
try:
    text_trocr = processor._process_hf_local(image, "handwritten")
    print(f"[TROCR RESULT]:\n'{text_trocr}'")
except Exception as e:
    print(f"[TROCR ERROR]: {e}")

print("\n\n3. TESTANDO EASYOCR...")
try:
    text_easy = processor._process_easyocr(image_bytes)
    print(f"[EASYOCR RESULT]:\n'{text_easy}'")
except Exception as e:
    print(f"[EASYOCR ERROR]: {e}")
