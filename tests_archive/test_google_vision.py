from google.cloud import vision
import io
import os

# Caminho da imagem de teste (usando a que sabemos que funciona)
image_path = "C:/Users/rafae/.gemini/antigravity/brain/92778fc1-5d28-41a2-a6ac-d0856d1a1855/pedido_medico_teste_1769524367458.png"

def test_vision_api():
    print("--- INICIANDO TESTE GOOGLE CLOUD VISION ---")
    try:
        # Instancia cliente (usa credenciais padrão do ambiente)
        client = vision.ImageAnnotatorClient()
        print("✅ Cliente instanciado.")

        # Carrega imagem
        with io.open(image_path, 'rb') as image_file:
            content = image_file.read()
        
        image = vision.Image(content=content)

        # Realiza detecção de texto denso (Document Text Detection)
        print("⏳ Enviando imagem para API...")
        response = client.document_text_detection(image=image)
        
        if response.error.message:
            print(f"❌ Erro na API: {response.error.message}")
            return

        text = response.full_text_annotation.text
        print("\n--- TEXTO EXTRAÍDO ---")
        print(text[:200] + "..." if len(text) > 200 else text)
        print("\n✅ SUCESSO! A API Vision está ativa e acessível.")

    except Exception as e:
        print(f"❌ Falha no teste: {e}")
        # Dica para user
        if "PermissionDenied" in str(e) or "not enabled" in str(e):
             print("\n⚠️ AVISO: A API 'Cloud Vision API' pode não estar ativada no projeto.")
             print("Acesse: https://console.cloud.google.com/apis/library/vision.googleapis.com?project=high-nature-319701")

if __name__ == "__main__":
    test_vision_api()
