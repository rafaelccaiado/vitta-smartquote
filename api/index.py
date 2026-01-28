from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import sys

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import local modules
try:
    from ocr_processor import OCRProcessor
except ImportError:
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
    return {
        "status": "online",
        "mode": "Vercel Monolith V22",
        "ocr_ready": ocr_processor is not None
    }

@app.post("/api/ocr")
async def process_ocr(file: UploadFile = File(...)):
    if not ocr_processor:
        return {"error": "OCR Processor not initialized"}
    
    contents = await file.read()
    return ocr_processor.process_image(contents)

# Handler for Vercel
# Vercel entry point
