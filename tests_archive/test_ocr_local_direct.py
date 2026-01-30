from ocr_processor import OCRProcessor
import os

print("Iniciando teste local do OCRProcessor...")

try:
    processor = OCRProcessor()
    
    image_path = "C:/Users/rafae/.gemini/antigravity/brain/92778fc1-5d28-41a2-a6ac-d0856d1a1855/uploaded_media_1_1769527620916.png"
    
    if os.path.exists(image_path):
        print(f"Lendo imagem: {image_path}")
        with open(image_path, "rb") as f:
            image_bytes = f.read()
        
        print("Executando process_image...")
        result = processor.process_image(image_bytes)
        
        print("\nResultado do OCR:")
        print(result)
        
        if result.get("text"):
            print("SUCESSO: Texto extraído!")
        else:
            print("AVISO: Texto vazio retornado.")
    else:
        print(f"Erro: Imagem não encontrada em {image_path}")

except Exception as e:
    print(f"ERRO FATAL no teste: {e}")
    import traceback
    traceback.print_exc()
