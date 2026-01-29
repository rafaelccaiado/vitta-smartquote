
import sys
import os

# Adicionar o diretório pai ao path para importar módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.ocr_processor import OCRProcessor

def debug_run():
    print("--- STARTING DEBUG RUN ---")
    
    # Simula inicialização
    processor = OCRProcessor()
    
    # Caminho da imagem (hardcoded para a última imagem enviada pelo usuário)
    img_path = r"C:/Users/rafae/.gemini/antigravity/brain/f5ac5d6f-7432-4c47-898d-d4a0d8a9e5b2/uploaded_media_1769708029787.png"
    
    if not os.path.exists(img_path):
        print(f"❌ Imagem não encontrada: {img_path}")
        return

    print(f"📸 Processando imagem: {img_path}")
    with open(img_path, "rb") as f:
        img_bytes = f.read()
        
    result = processor.process_image(img_bytes)
    
    print("\n--- RESULTADO FINAL ---")
    print(result.get("text"))
    print("\n--- ESTATÍSTICAS ---")
    print(result.get("stats"))
    print("\n--- DEBUG INFO ---")
    for line in result.get("lines", []):
         print(f"[{line['confidence']:.2f}] {line['corrected']} (Original: {line['original']})")

if __name__ == "__main__":
    debug_run()
