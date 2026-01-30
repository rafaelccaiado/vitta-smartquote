from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import sys

# Standardize python path for Vercel
# Vercel deploys the contents of 'api/' as functions. 
# We add the root of the repo (parent of api) to path if needed, 
# but usually 'api' is already in path as the root of the lambda.
base_dir = os.path.dirname(os.path.abspath(__file__))
if base_dir not in sys.path:
    sys.path.append(base_dir)

# Decoupled Imports (V70.7 - Core Isolation)
_init_error = None 

try:
    # Use relative-like absolute imports within the api/ root
    from core.ocr_processor import OCRProcessor
    from core.bigquery_client import BigQueryClient
    from core.validation_logic import ValidationService
    from services.learning_service import learning_service
except Exception as e:
    import traceback
    print(f"⚠️ Critical Backend Import Error: {e}")
    print(traceback.format_exc())
    _init_error = f"Backend Import Error: {str(e)}"

# PDCA Service (Optional)
try:
    from services.pdca_service import pdca_service
except Exception as e:
    print(f"⚠️ PDCA Service Import Error: {e}")
    pdca_service = None

app = FastAPI(title="Vitta SmartQuote API (Vercel)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances for reuse
_ocr_p = None
_bq_c = None

def get_services():
    global _ocr_p, _bq_c, _init_error
    try:
        if _ocr_p is None:
            # Import again if needed or use pre-imported
            from core.ocr_processor import OCRProcessor as Proc
            _ocr_p = Proc()
        if _bq_c is None:
            from core.bigquery_client import BigQueryClient as BQ
            _bq_c = BQ()
    except Exception as e:
        print(f"❌ Error initializing services: {e}")
        if not _init_error: _init_error = str(e)
    return _ocr_p, _bq_c

@app.get("/api/health")
async def health_check():
    ocr_p, bq_c = get_services()
    return {
        "status": "online",
        "mode": "Vercel Core Isolation V70.7",
        "ocr_ready": ocr_p is not None,
        "bq_ready": bq_c is not None,
        "init_error": _init_error
    }

@app.post("/api/validate-list")
async def validate_list(data: dict):
    ocr_p, bq_c = get_services()
    if bq_c is None:
        raise HTTPException(status_code=500, detail=f"BigQuery Client not ready: {_init_error}")
    
    terms = data.get("terms", [])
    unit = data.get("unit", "Goiânia Centro")
    
    from core.validation_logic import ValidationService
    return ValidationService.validate_batch(terms, unit, bq_c)

@app.post("/api/search-exams")
async def search_exams_endpoint(data: dict):
    _, bq_c = get_services()
    if not bq_c: raise HTTPException(status_code=500, detail="BQ Fail")
    term = data.get("term", "")
    unit = data.get("unit", "Goiânia Centro")
    return bq_c.search_exams(term, unit)

@app.post("/api/ocr")
async def ocr_endpoint(file: UploadFile = File(...)):
    ocr_p, _ = get_services()
    if not ocr_p: raise HTTPException(status_code=500, detail="OCR Fail")
    image_bytes = await file.read()
    return ocr_p.process_image(image_bytes)

@app.get("/api/pdca/logs")
async def get_pdca_logs():
    if pdca_service:
        return {"logs": pdca_service.logs}
    return {"logs": [], "error": "PDCA service unavailable"}

@app.get("/api/qa-proof")
async def qa_proof_endpoint():
    return {
        "build_id": "PROD-CORE-ISOLATION-V70.7",
        "status": "ok",
        "monolith": True
    }
