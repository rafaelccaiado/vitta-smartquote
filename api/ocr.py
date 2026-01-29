from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import JSONResponse
import os
import sys
import traceback

# 1. SETUP DE PATH
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 2. APP FACTORY
app = FastAPI()

# 3. IMPORT PIPELINE
OCRProcessor = None
PIPELINE_STATUS = "UNKNOWN"
IMPORT_ERROR = None

try:
    from ocr_processor import OCRProcessor
    PIPELINE_STATUS = "READY"
except ImportError as e:
    PIPELINE_STATUS = "IMPORT_ERROR"
    IMPORT_ERROR = str(e)
    print(f"❌ Critical Import Error: {e}")
    traceback.print_exc()
except Exception as e:
    PIPELINE_STATUS = "INIT_ERROR"
    IMPORT_ERROR = str(e)
    print(f"❌ Init Error: {e}")

# SINGLETON
_processor_instance = None
def get_processor():
    global _processor_instance
    if _processor_instance is None:
        if OCRProcessor:
            try:
                _processor_instance = OCRProcessor()
            except Exception as e:
                print(f"❌ Instantiation Error: {e}")
                traceback.print_exc()
                return None
    return _processor_instance

# 4. HEADERS E RESPONSE HELPERS (ASSINATURA DE PRODUÇÃO)
CACHE_HEADERS = {
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "Pragma": "no-cache",
    "Expires": "0",
    "X-Backend-Version": "V81.1-Fallback-System",
    "X-OCR-Entrypoint": "api/ocr.py",
    "X-OCR-Commit": "PROD-PROOF-v81.1"
}

def make_response(content: dict, status_code: int = 200):
    base = {
        "text": "",
        "lines": [],
        "confidence": 0.0,
        "stats": {"total_ocr_lines": 0, "classified_exams": 0, "valid_matches": 0},
        "debug_meta": {},
        "backend_version": "V81.1-Fallback-System"
    }
    base.update(content)
    
    # Injeção forçada de metadados de prova
    if "debug_meta" not in base:
        base["debug_meta"] = {}
        
    base["debug_meta"]["entrypoint"] = "api/ocr.py"
    base["debug_meta"]["commit"] = "PROD-PROOF-v81.1"
    
    return JSONResponse(content=base, status_code=status_code, headers=CACHE_HEADERS)

# 5. HANDLERS LÓGICOS

async def shared_health_check(request: Request, route_name: str):
    processor = get_processor()
    dic_size = 0
    if processor and hasattr(processor, "exams_flat_list"):
        dic_size = len(processor.exams_flat_list)
        
    return make_response({
        "status": "online",
        "description": "Vercel OCR Endpoint (Signed & Double Routed)",
        "debug_meta": {
            "route_hit": route_name,
            "request_path": str(request.url.path),
            "pipeline_status": PIPELINE_STATUS,
            "dictionary_loaded": dic_size > 0,
            "dictionary_size": dic_size,
            "init_error": IMPORT_ERROR
        }
    })

async def shared_ocr_handler(file: UploadFile, request: Request, route_name: str):
    meta = {
        "route_hit": route_name,
        "request_path": str(request.url.path),
        "dictionary_loaded": False,
        "dictionary_size": 0,
        "raw_ocr_lines": 0,
        "fallback_used": False,
        "pipeline_status": PIPELINE_STATUS,
        "error": None
    }

    # A) Pipeline Check
    if PIPELINE_STATUS != "READY":
        meta["error"] = f"Pipeline Error: {PIPELINE_STATUS} - {IMPORT_ERROR}"
        return make_response({"error": meta["error"], "debug_meta": meta}, status_code=200)

    processor = get_processor()
    if not processor:
        meta["error"] = "OCR Processor Init Failed"
        return make_response({"error": meta["error"], "debug_meta": meta}, status_code=200)

    # Dictionary Stats
    try:
        if hasattr(processor, "exams_flat_list") and processor.exams_flat_list:
            meta["dictionary_loaded"] = True
            meta["dictionary_size"] = len(processor.exams_flat_list)
    except:
        pass

    # B) Read File
    try:
        contents = await file.read()
    except Exception as e:
        meta["error"] = f"Upload Error: {e}"
        return make_response({"error": meta["error"], "debug_meta": meta}, status_code=200)

    # C) Execute
    try:
        result = processor.process_image(contents)
    except Exception as e:
        meta["error"] = f"Execution Error: {e}"
        traceback.print_exc()
        return make_response({"error": meta["error"], "debug_meta": meta}, status_code=200)

    # D) Validating & Fallback
    stats = result.get("stats", {})
    if stats:
        meta["raw_ocr_lines"] = stats.get("total_ocr_lines", 0)
        meta["classified_exams"] = stats.get("classified_exams", 0)
        meta["valid_matches"] = stats.get("valid_matches", 0)
    elif "debug_meta" in result and "raw_ocr_lines" in result["debug_meta"]:
         meta["raw_ocr_lines"] = result["debug_meta"]["raw_ocr_lines"]

    vision_saw_text = meta["raw_ocr_lines"] > 0
    result_lines = result.get("lines", [])
    result_is_empty = len(result_lines) == 0

    if vision_saw_text and result_is_empty:
        meta["fallback_used"] = True
        candidates = result.get("debug_raw", [])
        fallback_lines = []
        
        if candidates:
            for text in candidates:
                fallback_lines.append({
                    "original": text,
                    "corrected": f"[⚠️ Não Verificado] {text}",
                    "confidence": 0.1,
                    "method": "emergency_llm"
                })
        else:
             raw_text = result.get("text", "")
             if raw_text:
                 fallback_lines.append({
                     "original": "Raw Text",
                     "corrected": f"[⚠️ Não Verificado] {raw_text[:100]}...",
                     "confidence": 0.1,
                     "method": "emergency_text"
                 })
             else:
                 fallback_lines.append({
                     "original": "Erro",
                     "corrected": "[⚠️ Erro de Extração] Conteúdo detectado mas não processável.",
                     "confidence": 0.0,
                     "method": "emergency_fail"
                 })

        result["lines"] = fallback_lines
        result["text"] = "\n".join([l["corrected"] for l in fallback_lines])
        result["backend_version"] += " (Emergency)"

    # E) Merge Meta
    if "debug_meta" not in result:
        result["debug_meta"] = {}
    result["debug_meta"].update(meta)

    return make_response(result, status_code=200)

# 6. ROTAS DUPLAS (DOUBLE ROUTING)

@app.get("/")
async def root_health(request: Request):
    return await shared_health_check(request, "GET /")

@app.get("/api/ocr")
async def explicit_health(request: Request):
    return await shared_health_check(request, "GET /api/ocr")

@app.post("/")
async def root_ocr(request: Request, file: UploadFile = File(...)):
    return await shared_ocr_handler(file, request, "POST /")

@app.post("/api/ocr")
async def explicit_ocr(request: Request, file: UploadFile = File(...)):
    return await shared_ocr_handler(file, request, "POST /api/ocr")
