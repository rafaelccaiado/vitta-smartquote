from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import os
import sys
import traceback

# Standardize python path for Vercel
base_dir = os.path.dirname(os.path.abspath(__file__)) # /api
if base_dir not in sys.path:
    sys.path.append(base_dir)

# Delayed Imports to speed up cold start
_init_error = None
_ocr_p = None

try:
    from core.ocr_processor import OCRProcessor
    _ocr_p = OCRProcessor()
except Exception as e:
    _init_error = f"OCR Init Error: {str(e)}"
    print(f"❌ V86.0 Standalone OCR Fail: {traceback.format_exc()}")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/ocr")
async def ocr_endpoint(file: UploadFile = File(...)):
    if not _ocr_p:
        raise HTTPException(status_code=500, detail={
            "error": "OCR Not Initialized",
            "message": _init_error
        })
    try:
        image_bytes = await file.read()
        return _ocr_p.process_image(image_bytes)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Process Error: {str(e)}")

# Fallback for direct /ocr call
@app.post("/ocr")
async def ocr_fallback(file: UploadFile = File(...)):
    return await ocr_endpoint(file)
