
import sys
import os

# Ensure we are running from backend/ by adding current dir to sys.path
sys.path.append(os.getcwd())

try:
    from ocr_processor import OCRProcessor
except ImportError:
    # Fallback if running from parent
    sys.path.append(os.path.join(os.getcwd(), 'backend'))
    from ocr_processor import OCRProcessor

def run_test():
    print("--- STARTING BACKEND DEBUG RUN ---")
    try:
        processor = OCRProcessor()
    except Exception as e:
        print(f"❌ Failed to init processor: {e}")
        return

    # Use the specific uploaded image
    img_path = r"C:/Users/rafae/.gemini/antigravity/brain/f5ac5d6f-7432-4c47-898d-d4a0d8a9e5b2/uploaded_media_1769709568470.png"
    
    if not os.path.exists(img_path):
        print(f"❌ Image not found: {img_path}")
        return

    print(f"📸 Processing: {os.path.basename(img_path)}")
    with open(img_path, "rb") as f:
        img_bytes = f.read()

    result = processor.process_image(img_bytes)
    
    print("\n--- RESULTADO FINAL ---")
    if "error" in result:
        print(f"❌ Erro: {result['error']}")
    else:
        print(f"✅ Text Length: {len(result.get('text', ''))}")
        print(f"✅ Confidence: {result.get('confidence')}")
        print("--- EXTRACTED LINES ---")
        for line in result.get("lines", []):
            print(f"  [{line['confidence']:.2f}] {line['corrected']}")

if __name__ == "__main__":
    run_test()
