from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import os
import sys
import traceback

# Standardize python path for Vercel
# Returning to api/index.py structure
base_dir = os.path.dirname(os.path.abspath(__file__)) # this is /api
if base_dir not in sys.path:
    sys.path.append(base_dir)

# Deep Diagnostics V81.0 - Backend Restoration
_init_error = None
_traceback = None
_ocr_p = None
_bq_c = None

# Delayed/Safe Imports
try:
    print("🚀 V81.0: Starting Backend Restoration (api/index.py)...")
    from core.ocr_processor import OCRProcessor
    from core.bigquery_client import BigQueryClient
    from core.validation_logic import ValidationService
    from services.learning_service import learning_service
    from services.pdca_service import pdca_service
    print("✅ V81.0: Core imports successful.")
except Exception as e:
    _init_error = f"Import Error: {str(e)}"
    _traceback = traceback.format_exc()
    print(f"❌ V81.0 Import Fail: {_traceback}")

app = FastAPI(title="Vitta SmartQuote API (V81.0)")

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
        print(f"❌ V81.0 Init Fail: {_traceback}")
        return None, None

@app.get("/api/health")
async def health_check(request: Request):
    ocr_p, bq_c = get_services()
    return {
        "status": "online",
        "version": "V81.0",
        "path": str(request.url.path),
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

@app.post("/ocr")
async def ocr_endpoint_no_prefix(file: UploadFile = File(...)):
    return await ocr_endpoint(file)

@app.get("/api/qa-proof")
async def qa_proof_endpoint():
    return {"status": "ok", "diagnostics": "V81.0 Backend Ok"}

@app.get("/api")
async def root_api():
    return {"status": "ok", "message": "Vitta SmartQuote API V85.0 REACHABLE"}

@app.post("/api")
async def root_api_post(file: UploadFile = File(...)):
    # This handles the rewrite /api/(.*) -> /api which strips the subpath
    return await ocr_endpoint(file)

@app.get("/")
async def root():
    return await root_api()

@app.post("/")
async def root_post(file: UploadFile = File(...)):
    return await root_api_post(file)

# Fallback to handle any mapping issues
@app.api_route("/{path_name:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def catch_all(request: Request, path_name: str):
    return {
        "error": "Not Found in Monolith",
        "requested_path": path_name,
        "full_path": str(request.url.path),
        "method": request.method,
        "suggestion": "Check if route includes /api prefix",
        "version": "V84.0"
    }
