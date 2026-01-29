from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import JSONResponse
import os
import sys
import traceback
import time

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

# 4. HEADERS E RESPONSE HELPERS
CACHE_HEADERS = {
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "Pragma": "no-cache",
    "Expires": "0",
    "X-Backend-Version": "V81.1-Fallback-System",
    "X-OCR-Entrypoint": "api/ocr.py",
    "X-OCR-Commit": "PROD-TELEMETRY-v81.1"
}

def make_response(content: dict, status_code: int = 200):
    base = {
        "text": "",
        "lines": [],
        "confidence": 0.0,
        "stats": {"total_ocr_lines": 0, "classified_exams": 0, "valid_matches": 0},
        "debug_meta": {},
        "backend_version": "V81.1-Fallback-System",
        "error": None
    }
    base.update(content)
    
    # Garantir debug_meta básico
    if "debug_meta" not in base:
        base["debug_meta"] = {}
        
    base["debug_meta"]["entrypoint"] = "api/ocr.py"
    base["debug_meta"]["commit"] = "PROD-TELEMETRY-v81.1"
    
    # 200 OK sempre para Vercel não mostrar erro HTML
    return JSONResponse(content=base, status_code=200, headers=CACHE_HEADERS)

# 5. SHARED LOGIC

async def shared_health_check(request: Request, route_name: str):
    processor = get_processor()
    dic_size = 0
    if processor and hasattr(processor, "exams_flat_list"):
        dic_size = len(processor.exams_flat_list)
        
    return make_response({
        "status": "online",
        "description": "Vercel OCR Endpoint (Telemetry Enabled)",
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
    t_start = time.time()
    
    meta = {
        "route_hit": route_name,
        "request_path": str(request.url.path),
        "request_content_type": request.headers.get("content-type"),
        "file_filename": file.filename,
        "file_content_type": file.content_type,
        "file_size_bytes": 0,
        "read_bytes_ok": False,
        "decode_image_ok": False,
        "vision_called": False,
        "raw_ocr_lines_count": 0,
        "dictionary_loaded": False,
        "dictionary_size": 0,
        "fallback_used": False,
        "pipeline_status": PIPELINE_STATUS,
        "elapsed_ms_total": 0,
        "step_timings": {}
    }

    # 1. Pipeline Check
    if PIPELINE_STATUS != "READY":
        meta["elapsed_ms_total"] = (time.time() - t_start) * 1000
        return make_response({"error": f"Pipeline Error: {PIPELINE_STATUS} - {IMPORT_ERROR}", "debug_meta": meta})

    processor = get_processor()
    if not processor:
        meta["elapsed_ms_total"] = (time.time() - t_start) * 1000
        return make_response({"error": "OCR Processor Init Failed", "debug_meta": meta})

    # Stats do Dicionário
    try:
        t_dic = time.time()
        if hasattr(processor, "exams_flat_list") and processor.exams_flat_list:
            meta["dictionary_loaded"] = True
            meta["dictionary_size"] = len(processor.exams_flat_list)
        meta["step_timings"]["dictionary_check"] = (time.time() - t_dic) * 1000
    except:
        pass

    # 2. Read File
    try:
        t_read = time.time()
        contents = await file.read()
        file_size = len(contents)
        meta["file_size_bytes"] = file_size
        meta["read_bytes_ok"] = True
        meta["step_timings"]["read_file"] = (time.time() - t_read) * 1000

        if file_size == 0:
            meta["elapsed_ms_total"] = (time.time() - t_start) * 1000
            return make_response({"error": "Empty file upload", "debug_meta": meta})
            
    except Exception as e:
        meta["elapsed_ms_total"] = (time.time() - t_start) * 1000
        return make_response({"error": f"Upload Read Error: {str(e)}", "debug_meta": meta})

    # 3. Execute Pipeline
    try:
        t_exec = time.time()
        # Aqui assumimos que o processor lida com o decode interno
        # Mas podemos tentar validar decode antes se o processor falhar muito
        result = processor.process_image(contents)
        meta["step_timings"]["pipeline_total"] = (time.time() - t_exec) * 1000
        
        # Merge de metadados internos do processador, se houver
        if "debug_meta" in result:
             # Copiar chaves relevantes se existirem (ex: vision timings)
             pass 

        meta["vision_called"] = True # Assumimos chamado se não deu except
        
    except Exception as e:
        meta["elapsed_ms_total"] = (time.time() - t_start) * 1000
        traceback.print_exc()
        return make_response({"error": f"Pipeline Execution Error: {str(e)}", "debug_meta": meta})

    # 4. Validar Resultado e Fallback
    stats = result.get("stats", {})
    if stats:
        meta["raw_ocr_lines_count"] = stats.get("total_ocr_lines", 0)
        
    # Verificar redundância se debug_meta interno trouxer info
    if "debug_meta" in result and "raw_ocr_lines" in result["debug_meta"]:
         meta["raw_ocr_lines_count"] = result["debug_meta"]["raw_ocr_lines"]

    vision_saw_text = meta["raw_ocr_lines_count"] > 0
    result_lines = result.get("lines", [])
    result_is_empty = len(result_lines) == 0

    if vision_saw_text and result_is_empty:
        meta["fallback_used"] = True
        input_candidates = result.get("debug_raw", [])
        fallback_lines = []
        
        if input_candidates:
            for text in input_candidates:
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

    meta["elapsed_ms_total"] = (time.time() - t_start) * 1000
    
    # Merge Final
    if "debug_meta" not in result:
        result["debug_meta"] = {}
    result["debug_meta"].update(meta)

    return make_response(result)

# 6. ROTAS DUPLAS

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
