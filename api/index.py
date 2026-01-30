from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import sys

# Add directory and core to path
base_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(base_dir)
sys.path.append(os.path.join(base_dir, "core"))

# Decoupled Imports (V70.6 - Core Path)
OCRProcessor = None
_init_error = None 

try:
    from core.ocr_processor import OCRProcessor
except Exception as e:
    print(f"❌ Critical OCR Import Error: {e}")
    _init_error = f"Import Error: {str(e)}"

BigQueryClient = None
ValidationService = None
learning_service = None

try:
    from core.bigquery_client import BigQueryClient
    from core.validation_logic import ValidationService
    from services.learning_service import learning_service
except Exception as e:
    import traceback
    print(f"⚠️ Validation/Backend Import Error: {e}")
    print(traceback.format_exc())
    if not _init_error: _init_error = f"Backend Import Error: {str(e)}"

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

_ocr_processor_instance = None
_bq_client_instance = None

def get_ocr_processor():
    global _ocr_processor_instance, _init_error, OCRProcessor
    if OCRProcessor is None:
        try:
            from core.ocr_processor import OCRProcessor as DynamicOCR
            OCRProcessor = DynamicOCR
        except Exception as import_err:
            _init_error = f"Lazy Import Failed: {import_err}"
            return None

    if _ocr_processor_instance is None and OCRProcessor:
        try:
            _ocr_processor_instance = OCRProcessor()
        except Exception as e:
            _init_error = f"Instantiation Error: {e}"
    return _ocr_processor_instance

def get_bq_client():
    global _bq_client_instance
    if _bq_client_instance is None and BigQueryClient:
        try:
            _bq_client_instance = BigQueryClient()
        except Exception as e:
            print(f"❌ BQ Init Fail: {e}")
    return _bq_client_instance

@app.get("/api/health")
async def health_check():
    ocr_p = get_ocr_processor()
    bq_c = get_bq_client()
    return {
        "status": "online",
        "mode": "Vercel Core Isolation V70.6",
        "ocr_ready": ocr_p is not None,
        "bq_ready": bq_c is not None,
        "init_error": _init_error,
        "python_path": sys.path[-3:]
    }

@app.post("/api/validate-list")
async def validate_list(data: dict):
    try:
        bq_c = get_bq_client()
        if bq_c is None or ValidationService is None:
            raise HTTPException(status_code=500, detail=f"Services not initialized: {_init_error}")
            
        terms = data.get("terms", [])
        unit = data.get("unit", "Goiânia Centro")
        result = ValidationService.validate_batch(terms, unit, bq_c)
        return result
    except Exception as e:
        import traceback
        return HTTPException(status_code=500, detail=str(e))

@app.post("/api/search-exams")
async def search_exams_endpoint(data: dict):
    try:
        bq_c = get_bq_client()
        if not bq_c: raise Exception("BQ Fail")
        term = data.get("term", "")
        unit = data.get("unit", "Goiânia Centro")
        return bq_c.search_exams(term, unit)
    except Exception as e:
        return {"error": str(e)}

@app.get("/api/pdca/logs")
async def get_pdca_logs():
    if pdca_service:
        return {"logs": pdca_service.logs}
    return {"logs": [], "error": "PDCA service unavailable"}

@app.get("/api/qa-proof")
async def qa_proof_endpoint():
    return {
        "build_id": "PROD-CORE-ISOLATION-V70.6",
        "status": "ok",
        "monolith": True
    }
