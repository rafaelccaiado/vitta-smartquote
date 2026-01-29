from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import sys

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Decoupled Imports for Robustness (V42)
OCRProcessor = None
try:
    from ocr_processor import OCRProcessor
except Exception as e:
    print(f"❌ Critical OCR Import Error: {e}")

BigQueryClient = None
ValidationService = None
learning_service = None

try:
    from bigquery_client import BigQueryClient
    from validation_logic import ValidationService
    from services.learning_service import learning_service
except Exception as e:
    print(f"⚠️ Validation/Backend Import Error: {e}")
    # We continue without validation features if this fails, but OCR should survive


app = FastAPI(title="Vitta SmartQuote API (Vercel)")

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Clients (LAZY V70.2)
_ocr_processor_instance = None
_bq_client_instance = None

_init_error = None

def get_ocr_processor():
    global _ocr_processor_instance, _init_error
    if _ocr_processor_instance is None and OCRProcessor:
        try:
            _ocr_processor_instance = OCRProcessor()
            print("✅ OCR Init Success")
        except Exception as e:
            _init_error = str(e)
            print(f"❌ OCR Init Fail: {e}")
    return _ocr_processor_instance

def get_bq_client():
    global _bq_client_instance
    if _bq_client_instance is None and BigQueryClient:
        try:
            _bq_client_instance = BigQueryClient()
            print("✅ BigQuery Init Success")
        except Exception as e:
            print(f"❌ BigQuery Init Fail: {e}")
    return _bq_client_instance


@app.get("/api/health")
def health_check():
    import base64
    env_key = os.getenv("GCP_SA_KEY_BASE64")
    key_status = "MISSING"
    if env_key:
        try:
            base64.b64decode(env_key)
            key_status = "PRESENT"
        except:
            key_status = "INVALID_B64"

    ocr_p = get_ocr_processor()
    bq_c = get_bq_client()
    
    return {
        "status": "online",
        "mode": "Vercel Monolith V70.2 (Lazy Init)",
        "ocr_ready": ocr_p is not None,
        "bq_ready": bq_c is not None,
        "env_check": {
            "GCP_SA_KEY_BASE64": key_status,
        }
    }

from fastapi import Response

@app.post("/api/ocr")
async def process_ocr(response: Response, file: UploadFile = File(...), unit: str = "Goiânia Centro"):
    # Anti-Cache Headers (V81.1)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"

    ocr_p = get_ocr_processor()
    if not ocr_p:
        global _init_error
        return {"error": f"OCR Processor Init Failed (Vercel). Details: {_init_error}"}
    
    contents = await file.read()
    return ocr_p.process_image(contents)

@app.get("/api/units")
async def get_units():
    try:
        bq_c = get_bq_client()
        if not bq_c:
             # Fallback temporarily if BQ is down
             return {"units": ["Goiânia Centro", "Anápolis", "Trindade"]}
        
        units = bq_c.get_units()
        return {"units": units}
    except Exception as e:
        print(f"Erro get-units: {e}")
        return {"units": ["Goiânia Centro (Fallback)"]}


@app.post("/api/validate-list")
async def validate_list(data: dict):
    try:
        bq_c = get_bq_client()
        if not bq_c:
             raise Exception("BigQuery Client not initialized")
             
        terms = data.get("terms", [])
        unit = data.get("unit", "Goiânia Centro")
        
        # ValidationService agora está na pasta local
        result = ValidationService.validate_batch(terms, unit, bq_c)
        return result
    except Exception as e:
        print(f"Erro validate-list: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/search-exams")
async def search_exams_endpoint(data: dict):
    try:
        bq_c = get_bq_client()
        if not bq_c:
             raise Exception("BigQuery Client not initialized")

        term = data.get("term", "")
        unit = data.get("unit", "Goiânia Centro")
        
        if not term:
            return {"exams": []}
            
        exams = bq_c.search_exams(term, unit)
        return {"exams": exams, "count": len(exams)}
    except Exception as e:
        print(f"Erro search-exams: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/learn-correction")
async def learn_correction(data: dict):
    try:
        original = data.get("original_term")
        correct = data.get("correct_exam_name")
        if original and correct and learning_service:
            learning_service.learn(original, correct)
            return {"status": "success"}
        return {"status": "ignored"}
    except:
        return {"status": "error"}

