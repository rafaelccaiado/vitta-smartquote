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

# Initialize Clients
ocr_processor = None
bq_client = None

if OCRProcessor:
    try:
        ocr_processor = OCRProcessor()
        print("✅ OCR Init Success")
    except Exception as e:
        print(f"❌ OCR Init Fail: {e}")

if BigQueryClient:
    try:
        bq_client = BigQueryClient()
        print("✅ BigQuery Init Success")
    except Exception as e:
        print(f"❌ BigQuery Init Fail: {e}")


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

    return {
        "status": "online",
        "mode": "Vercel Monolith V40 (Full Backend)",
        "ocr_ready": ocr_processor is not None,
        "bq_ready": bq_client is not None,
        "env_check": {
            "GCP_SA_KEY_BASE64": key_status,
        }
    }

@app.post("/api/ocr")
async def process_ocr(file: UploadFile = File(...), unit: str = "Goiânia Centro"):
    if not ocr_processor:
        return {"error": "OCR Processor not initialized"}
    contents = await file.read()
    return ocr_processor.process_image(contents)

@app.post("/api/validate-list")
async def validate_list(data: dict):
    # Recebe { "terms": ["hemograma", ...], "unit": "..." }
    try:
        if not bq_client:
             raise Exception("BigQuery Client not initialized")
             
        terms = data.get("terms", [])
        unit = data.get("unit", "Goiânia Centro")
        
        # ValidationService agora está na pasta local
        result = ValidationService.validate_batch(terms, unit, bq_client)
        return result
    except Exception as e:
        print(f"Erro validate-list: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/search-exams")
async def search_exams_endpoint(data: dict):
    try:
        if not bq_client:
             raise Exception("BigQuery Client not initialized")

        term = data.get("term", "")
        unit = data.get("unit", "Goiânia Centro")
        
        if not term:
            return {"exams": []}
            
        exams = bq_client.search_exams(term, unit)
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

