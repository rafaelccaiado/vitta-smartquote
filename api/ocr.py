from fastapi import FastAPI, UploadFile, File, Response
from fastapi.responses import JSONResponse
import os
import sys
import traceback
import json

# 1. PATH SETUP (Critical for Vercel/Lambda)
# Ensures imports find 'api/ocr_processor.py' and 'api/services/'
# Security Note: We only add the strict parent directory of this file
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 2. APP INITIALIZATION
app = FastAPI()

# 3. IMPORT PIPELINE (V81.1)
OCRProcessor = None
PIPELINE_STATUS = "UNKNOWN"
IMPORT_ERROR = None

try:
    from ocr_processor import OCRProcessor
    PIPELINE_STATUS = "READY"
except ImportError as e:
    PIPELINE_STATUS = "IMPORT_ERROR"
    IMPORT_ERROR = str(e)
    print(f"❌ Critical Import Error in api/ocr.py: {e}")
    traceback.print_exc()
except Exception as e:
    PIPELINE_STATUS = "INIT_ERROR"
    IMPORT_ERROR = str(e)
    print(f"❌ Erro Desconhecido na Importação: {e}")

# 4. SINGLETON INSTANCE (Cold Start Optimization)
_processor_instance = None

def get_processor():
    global _processor_instance
    if _processor_instance is None:
        if OCRProcessor:
            try:
                _processor_instance = OCRProcessor()
                print("✅ OCRProcessor initialized successfully (Cold Start)")
            except Exception as e:
                print(f"❌ OCRProcessor instantiation failed: {e}")
                traceback.print_exc()
                return None
    return _processor_instance

# 5. HEADER HELPER
def add_anti_cache_headers(response: Response):
    # P1 Risk: Stale Vercel Cache
    # Mitigation: Aggressive no-store directives
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    response.headers["X-Backend-Version"] = "V81.1-Fallback-System"

# 6. ROUTE HANDLER (Must be "/" for Vercel file-based routing)
@app.post("/")
async def ocr_handler(response: Response, file: UploadFile = File(...), unit: str = "Goiânia Centro"):
    
    # Init Anti-Cache
    add_anti_cache_headers(response)
    
    # Metadata Container (Guaranteed Structure)
    meta = {
        "backend_version": "V81.1-Fallback-System",
        "dictionary_loaded": False,
        "dictionary_size": 0,
        "raw_ocr_lines": 0,
        "fallback_used": False,
        "pipeline_status": PIPELINE_STATUS,
        "error": None
    }

    # A) Check Processor Logic
    if PIPELINE_STATUS != "READY":
        meta["error"] = f"Pipeline not ready. Status: {PIPELINE_STATUS}. Details: {IMPORT_ERROR}"
        return JSONResponse(status_code=503, content={"error": meta["error"], "debug_meta": meta})

    processor = get_processor()
    if not processor:
        meta["error"] = "OCR Processor Class could not be instantiated"
        return JSONResponse(status_code=503, content={"error": meta["error"], "debug_meta": meta})

    # Update Meta from Processor Internal State (White-box check)
    try:
        if hasattr(processor, "exams_flat_list") and processor.exams_flat_list:
            meta["dictionary_loaded"] = True
            meta["dictionary_size"] = len(processor.exams_flat_list)
    except:
        pass # Non-critical

    # B) Read File Securely
    try:
        contents = await file.read()
    except Exception as e:
        meta["error"] = f"File Read Error: {e}"
        return JSONResponse(status_code=400, content={"error": meta["error"], "debug_meta": meta})

    # C) Execute Pipeline Protected
    try:
        # Expected to return dict with keys: text, lines, confidence, stats, debug_meta...
        result = processor.process_image(contents)
    except Exception as e:
        meta["error"] = f"Pipeline Execution Error: {e}"
        print(f"❌ Pipeline Failed: {e}")
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": meta["error"], "debug_meta": meta})

    # D) Validating & Enriching Result (The "Never Empty" Guarantee)
    
    # D.1) Extract stats safely
    stats = result.get("stats", {})
    if stats:
        meta["raw_ocr_lines"] = stats.get("total_ocr_lines", 0)
        meta["classified_exams"] = stats.get("classified_exams", 0)
        meta["valid_matches"] = stats.get("valid_matches", 0)
    elif "debug_meta" in result and "raw_ocr_lines" in result["debug_meta"]:
         meta["raw_ocr_lines"] = result["debug_meta"]["raw_ocr_lines"]
    
    # D.2) EMERGENCY FALLBACK TRIGGER
    # Triggered IF: The Vision API saw text (>0 lines) BUT the final result 'lines' list is empty.
    vision_saw_text = meta["raw_ocr_lines"] > 0
    result_lines = result.get("lines", [])
    result_is_empty = len(result_lines) == 0

    if vision_saw_text and result_is_empty:
        print("⚠️ Emergency Fallback Triggered in Entrypoint (Hardened)")
        meta["fallback_used"] = True
        
        # Try to salvage text from debug_raw (LLM candidates) or stats
        candidates = result.get("debug_raw", [])
        
        fallback_lines = []
        if candidates:
            for text in candidates:
                fallback_lines.append({
                    "original": text,
                    "corrected": f"[⚠️ Não Verificado] {text}",
                    "confidence": 0.1,
                    "method": "emergency_fallback_candidates"
                })
        else:
             # Last resort: Try raw text from result if available, or generic error
             raw_text_backup = result.get("text", "")
             if raw_text_backup:
                  fallback_lines.append({
                     "original": "Texto bruto recuperado",
                     "corrected": f"[⚠️ Não Verificado] {raw_text_backup[:100]}...",
                     "confidence": 0.1,
                     "method": "emergency_fallback_text"
                 })
             else:
                 fallback_lines.append({
                     "original": "Texto detectado mas perdido no pipeline",
                     "corrected": "[⚠️ Erro Crítico] Texto detectado mas não processado. Tente novamente.",
                     "confidence": 0.0,
                     "method": "emergency_failure"
                 })

        result["lines"] = fallback_lines
        result["text"] = "\n".join([l["corrected"] for l in fallback_lines])
        result["backend_version"] = meta["backend_version"] + " (Emergency)"

    # E) Merge Metadata Finalization
    # Ensure consistent structure
    if "debug_meta" not in result:
        result["debug_meta"] = {}
    
    result["debug_meta"].update(meta)
    
    # Force version tag one last time
    result["backend_version"] = result.get("backend_version", meta["backend_version"])

    return JSONResponse(content=result)
