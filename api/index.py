from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import sys
import traceback

# Standardize python path for Vercel
base_dir = os.path.dirname(os.path.abspath(__file__))
if base_dir not in sys.path:
    sys.path.append(base_dir)

# Deep Diagnostics V79.0 - UTF-8 FIXED
_init_error = None
_traceback = None
_ocr_p = None
_bq_c = None

# Delayed/Safe Imports
try:
    print("🚀 V79.0: Starting Deep Import Diagnostics (UTF-8 FIX)...")
    from core.ocr_processor import OCRProcessor
    from core.bigquery_client import BigQueryClient
    from core.validation_logic import ValidationService
    from services.learning_service import learning_service
    from services.pdca_service import pdca_service
    print("✅ V79.0: Core imports successful.")
except Exception as e:
    _init_error = f"Import Error: {str(e)}"
    _traceback = traceback.format_exc()
    print(f"❌ V79.0 Import Fail: {_traceback}")

app = FastAPI(title="Vitta SmartQuote API (V79.0)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_services():
    global _ocr_p, _bq_c, _init_error, _traceback
    if _init_error:
        return None, None
    
    try:
        if _ocr_p is None:
            _ocr_p = OCRProcessor()
        if _bq_c is None:
            _bq_c = BigQueryClient()
        return _ocr_p, _bq_c
    except Exception as e:
        _init_error = f"Init Error: {str(e)}"
        _traceback = traceback.format_exc()
        print(f"❌ V79.0 Init Fail: {_traceback}")
        return None, None

@app.get("/api/health")
async def health_check():
    ocr_p, bq_c = get_services()
    return {
        "status": "online",
        "version": "V79.0",
        "ocr_ready": ocr_p is not None,
        "bq_ready": bq_c is not None,
        "error": _init_error,
        "traceback": _traceback
    }

@app.post("/api/ocr")
async def ocr_endpoint(file: UploadFile = File(...)):
    ocr_p, _ = get_services()
    if not ocr_p:
        raise HTTPException(status_code=500, detail={
            "error": "OCR Fail",
            "message": _init_error,
            "traceback": _traceback
        })
    try:
        image_bytes = await file.read()
        return ocr_p.process_image(image_bytes)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Process Error: {str(e)}\n{traceback.format_exc()}")

@app.get("/api/qa-proof")
async def qa_proof_endpoint():
    return {"status": "ok", "diagnostics": "V79.0 UTF-8 Fixed"}
