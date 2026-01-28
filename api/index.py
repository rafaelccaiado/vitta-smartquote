from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import sys

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import local modules
# Precisamos envolver em try/except porque o ocr_processor importa google.cloud no topo
try:
    from ocr_processor import OCRProcessor
except ImportError:
    OCRProcessor = None
except Exception as e:
    print(f"Erro importando OCRProcessor: {e}")
    OCRProcessor = None

app = FastAPI(title="Vitta SmartQuote API (Vercel)")

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ocr_processor = None
if OCRProcessor:
    try:
        ocr_processor = OCRProcessor()
        print("✅ OCR Init Success")
    except Exception as e:
        print(f"❌ OCR Init Fail: {e}")

@app.get("/api/health")
def health_check():
    import base64
    env_key = os.getenv("GCP_SA_KEY_BASE64")
    key_status = "MISSING"
    if env_key:
        try:
            base64.b64decode(env_key)
            key_status = "PRESENT_AND_VALID_B64"
        except:
            key_status = "PRESENT_BUT_INVALID_B64"

    return {
        "status": "online",
        "mode": "Vercel Monolith V26 (Diagnostic Mode)",
        "ocr_ready": ocr_processor is not None,
        "ocr_init_error": getattr(ocr_processor, "init_error", None) if ocr_processor else "Not Attempted",
        "env_check": {
            "GCP_SA_KEY_BASE64": key_status,
        }
    }

@app.post("/api/ocr")
async def process_ocr(file: UploadFile = File(...)):
    if not ocr_processor:
        return {
            "error": "OCR Processor not initialized",
            "detail": getattr(ocr_processor, "init_error", "Unknown Error") if ocr_processor else "Import Failed"
        }
    
    contents = await file.read()
    return ocr_processor.process_image(contents)
