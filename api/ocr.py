from fastapi import FastAPI, UploadFile, File, Response
from fastapi.responses import JSONResponse
import os
import sys
import traceback

# 1. PATH SETUP (Critical for Vercel/Lambda)
# Ensures imports find 'api/ocr_processor.py'
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 2. APP INITIALIZATION
app = FastAPI()

# 3. IMPORT PIPELINE (V81.1)
OCRProcessor = None
try:
    from ocr_processor import OCRProcessor
except ImportError as e:
    print(f"❌ Critical Import Error in api/ocr.py: {e}")
    traceback.print_exc()

# 4. SINGLETON INSTANCE (Cold Start Optimization)
_processor_instance = None

def get_processor():
    global _processor_instance
    if _processor_instance is None:
        if OCRProcessor:
            try:
                _processor_instance = OCRProcessor()
                print("✅ OCRProcessor initialized successfully")
            except Exception as e:
                print(f"❌ OCRProcessor initialization failed: {e}")
                traceback.print_exc()
    return _processor_instance

# 5. HEADER HELPER
def add_anti_cache_headers(response: Response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    response.headers["X-Backend-Version"] = "V81.1-Fallback-System"

# 6. ROUTE HANDLER (Must be "/" for Vercel file-based routing)
@app.post("/")
async def ocr_handler(response: Response, file: UploadFile = File(...), unit: str = "Goiânia Centro"):
    
    # Apply Headers Immediately
    add_anti_cache_headers(response)
    
    # Metadata Container
    meta = {
        "backend_version": "V81.1-Fallback-System",
        "dictionary_loaded": False,
        "dictionary_size": 0,
        "raw_ocr_lines": 0,
        "fallback_used": False,
        "error": None
    }

    # A) Check Processor
    processor = get_processor()
    if not processor:
        meta["error"] = "OCR Processor Class could not be initialized"
        return JSONResponse(status_code=503, content={"error": meta["error"], "debug_meta": meta})

    # Update Meta from Processor State
    try:
        if hasattr(processor, "exams_flat_list"):
            meta["dictionary_loaded"] = True
            meta["dictionary_size"] = len(processor.exams_flat_list)
    except:
        pass

    # B) Read File
    try:
        contents = await file.read()
    except Exception as e:
        meta["error"] = f"File Read Error: {e}"
        return JSONResponse(status_code=400, content={"error": meta["error"], "debug_meta": meta})

    # C) Execute Pipeline
    try:
        # Expected to return dict with keys: text, lines, confidence, stats, debug_meta...
        result = processor.process_image(contents)
    except Exception as e:
        meta["error"] = f"Pipeline Execution Error: {e}"
        traceback.print_exc()
        return JSONResponse(status_code=500, content={"error": meta["error"], "debug_meta": meta})

    # D) Validating & Enriching Result
    # Extract stats for metadata
    stats = result.get("stats", {})
    if stats:
        meta["raw_ocr_lines"] = stats.get("total_ocr_lines", 0)
        meta["classified_exams"] = stats.get("classified_exams", 0)
        meta["valid_matches"] = stats.get("valid_matches", 0)
    
    # E) EMERGENCY FALLBACK (The "Bulletproof" Layer)
    # Trigger: OCR saw text (lines > 0) BUT result 'lines' is empty
    vision_saw_text = meta["raw_ocr_lines"] > 0
    result_is_empty = len(result.get("lines", [])) == 0

    if vision_saw_text and result_is_empty:
        print("⚠️ Emergency Fallback Triggered in Entrypoint")
        meta["fallback_used"] = True
        
        # Try to salvage text from debug_raw (LLM candidates) or stats
        # Note: If OCRProcessor V81.1 did its job, output['debug_raw'] should have candidates
        candidates = result.get("debug_raw", [])
        
        fallback_lines = []
        if candidates:
            for text in candidates:
                fallback_lines.append({
                    "original": text,
                    "corrected": f"[⚠️ Não Verificado] {text}",
                    "confidence": 0.1,
                    "method": "entrypoint_fallback"
                })
        else:
             # Last resort: generic message if we can't even get candidates
             fallback_lines.append({
                 "original": "Texto detectado mas não classificado",
                 "corrected": "[⚠️ Erro de Processamento] Verifique a imagem manual",
                 "confidence": 0.0,
                 "method": "failure"
             })

        result["lines"] = fallback_lines
        result["text"] = "\n".join([l["corrected"] for l in fallback_lines])
        result["backend_version"] = meta["backend_version"] + " (Emergency)"

    # F) Merge Metadata
    # We prefer the processor's internal meta if available, but ensure our critical keys exist
    if "debug_meta" not in result:
        result["debug_meta"] = {}
    
    result["debug_meta"].update(meta)
    
    # Ensure top-level version tag
    result["backend_version"] = meta["backend_version"]

    return result
