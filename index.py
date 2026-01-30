from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import sys
import traceback

# Standardize python path for Vercel Monolith
# Now running from ROOT
base_dir = os.path.dirname(os.path.abspath(__file__))
api_dir = os.path.join(base_dir, "api")
if api_dir not in sys.path:
    sys.path.append(api_dir)

# Deep Diagnostics V80.0 - ROOT MONOLITH
_init_error = None
_traceback = None
_ocr_p = None
_bq_c = None

# Delayed/Safe Imports from api/ directory
try:
    print("🚀 V80.0: Starting Root Monolith (api/ folder in path)...")
    from core.ocr_processor import OCRProcessor
    from core.bigquery_client import BigQueryClient
    from core.validation_logic import ValidationService
    from services.learning_service import learning_service
    from services.pdca_service import pdca_service
    print("✅ V80.0: Core imports from api/ successful.")
except Exception as e:
    _init_error = f"Import Error: {str(e)}"
    _traceback = traceback.format_exc()
    print(f"❌ V80.0 Import Fail: {_traceback}")

app = FastAPI(title="Vitta SmartQuote API (V80.0 - Root Monolith)")

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
        print(f"❌ V80.0 Init Fail: {_traceback}")
        return None, None

@app.get("/api/health")
async def health_check():
    ocr_p, bq_c = get_services()
    return {
        "status": "online",
        "version": "V80.0",
        "location": "Root",
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
    return {"status": "ok", "diagnostics": "V80.0 Root Monolith"}
