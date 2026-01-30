from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import sys

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Decoupled Imports for Robustness (V42)
OCRProcessor = None
_init_error = None # Initialize global error

try:
    from ocr_processor import OCRProcessor
except Exception as e:
    print(f"❌ Critical OCR Import Error: {e}")
    _init_error = f"Import Error: {str(e)}"

BigQueryClient = None
ValidationService = None
learning_service = None

try:
    from bigquery_client import BigQueryClient
    from validation_logic import ValidationService
    from services.learning_service import learning_service
except Exception as e:
    import traceback
    print(f"⚠️ Validation/Backend Import Error: {e}")
    print(traceback.format_exc())
    if not _init_error: _init_error = f"Backend Import Error: {str(e)}"


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

# _init_error = None # REMOVIDO PARA NÃO APAGAR ERRO DE IMPORT ANTERIOR

def get_ocr_processor():
    global _ocr_processor_instance, _init_error, OCRProcessor
    
    # 1. Tentar importar se não estiver carregado (Active Lazy Load)
    if OCRProcessor is None:
        try:
            import importlib
            # Tenta limpar o cache do módulo se existir (reload forçado)
            if "ocr_processor" in sys.modules:
                importlib.reload(sys.modules["ocr_processor"])
            else:
                import ocr_processor
            
            # Pega classe
            if hasattr(sys.modules.get("ocr_processor"), "OCRProcessor"):
                OCRProcessor = sys.modules["ocr_processor"].OCRProcessor
            else:
                _init_error = "Module loaded but OCRProcessor class missing"
                return None
                
        except Exception as import_err:
            _init_error = f"Lazy Import Failed: {import_err}"
            print(f"❌ Lazy Import Error: {import_err}")
            return None

    # 2. Instanciar se necessário
    if _ocr_processor_instance is None and OCRProcessor:
        try:
            _ocr_processor_instance = OCRProcessor()
            print("✅ OCR Init Success (Lazy)")
        except Exception as e:
            _init_error = f"Instantiation Error: {e}"
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
        "init_error": _init_error, 
        "debug_probe": {
            "OCRProcessor_Type": str(type(OCRProcessor)),
            "OCRProcessor_Val": str(OCRProcessor),
            "Instance_Type": str(type(_ocr_processor_instance)),
            "Init_Error_Val": str(_init_error),
            "Modules_Loaded": "ocr_processor" in sys.modules
        },
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
        print(f"🕵️ BATCH DEBUG START")
        bq_c = get_bq_client()
        print(f" - BigQuery Client Type: {type(bq_c)}")
        print(f" - ValidationService Type: {type(ValidationService)}")
        
        if bq_c is None:
            raise Exception("ERROR: BigQuery Client (bq_c) is None")
        
        if ValidationService is None:
            error_details = _init_error or "Unknown Init Error"
            raise Exception(f"ERROR: ValidationService is None. Details: {error_details}")
            
        terms = data.get("terms", [])
        unit = data.get("unit", "Goiânia Centro")
        
        print(f" - Received Terms: {len(terms)} items")
        print(f" - Unit: '{unit}'")
        
        # ValidationService agora está na pasta local
        try:
            result = ValidationService.validate_batch(terms, unit, bq_c)
            print(" ✅ call to ValidationService.validate_batch completed")
        except Exception as inner_e:
            print(f" ❌ CRASH inside validate_batch: {inner_e}")
            import traceback
            print(traceback.format_exc())
            raise inner_e
        
        # Add debug info to response
        result["debug"] = {
            "input_count": len(terms),
            "unit_requested": unit,
            "catalog_count": 0
        }
        try:
            cat = bq_c.get_all_exams(unit)
            result["debug"]["catalog_count"] = len(cat)
        except Exception as cat_e:
             print(f" ⚠️ Failed to get catalog count for debug: {cat_e}")
        return result
    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        print(f"❌ Erro validate-list FULL TRACE:\n{error_msg}")
        # Retornamos o traceback completo no detalhe para ver no frontend
        raise HTTPException(status_code=500, detail=f"Traceback: {error_msg}")

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
        import traceback
        error_msg = traceback.format_exc()
        print(f"Erro search-exams: {e}")
        raise HTTPException(status_code=500, detail=f"Traceback: {error_msg}")

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

