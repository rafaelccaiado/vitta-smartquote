from http.server import BaseHTTPRequestHandler
from fastapi import FastAPI, UploadFile, File, HTTPException, Response
import os
import sys

# Ensure current directory is in path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the V81.1 Processor
try:
    from ocr_processor import OCRProcessor
except ImportError as e:
    print(f"CRITICAL IMPORT ERROR: {e}")
    OCRProcessor = None

app = FastAPI()

# Global Instance for caching (Lambda container reuse)
_processor = None

def get_processor():
    global _processor
    if _processor is None and OCRProcessor:
        try:
            _processor = OCRProcessor()
        except Exception as e:
            print(f"Processor Init Error: {e}")
            return None
    return _processor

@app.post("/api/ocr")
async def ocr_endpoint(response: Response, file: UploadFile = File(...), unit: str = "Goiânia Centro"):
    # 1. Anti-Cache Headers (Strict)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"

    # 2. Processor Initialization Check
    processor = get_processor()
    if not processor:
        return {
            "error": "OCR Processor Init Failed (api/ocr.py)",
            "backend_version": "V81.1-Fallback-System",
            "debug_meta": {
                "dictionary_loaded": False,
                "dictionary_size": 0,
                "raw_ocr_lines": 0,
                "fallback_used": False,
                "error": "Module Import or Class Init Failed"
            }
        }

    # 3. Read Content
    try:
        contents = await file.read()
    except Exception as e:
        return {"error": f"File Read Error: {str(e)}"}

    # 4. Execute Pipeline
    result = processor.process_image(contents)

    # 5. Fallback Guarantee (Extra check)
    # The processor should handle this, but we enforce specific response structure if needed
    if "backend_version" not in result:
        result["backend_version"] = "V81.1-Fallback-System"
    
    return result
