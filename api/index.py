from fastapi import FastAPI, UploadFile, File, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import os
import sys
import traceback

# Standardize python path for Vercel
base_dir = os.path.dirname(os.path.abspath(__file__))
if base_dir not in sys.path:
    sys.path.append(base_dir)

# Initialize FastAPI
app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "V90.0-CleanSweep"}

@app.get("/api/qa-proof")
async def qa_proof():
    return {"status": "ready", "engine": "Vitta SmartQuote REST Engine V90.0"}

# --- UPDATED ENDPOINTS (V90.0) ---

@app.post("/api/validate-list")
async def validate_list(request: Request):
    """Valida uma lista de termos de exames (Phase 4/5)."""
    try:
        from core.validation_logic import validation_service
        from core.bigquery_client import bq_client
        
        data = await request.json()
        terms = data.get("terms", [])
        unit = data.get("unit", "Goiânia Centro")
        
        # V90: Use batch validation for efficiency and consistency
        results_data = validation_service.validate_batch(terms, unit, bq_client)
            
        return results_data
    except Exception as e:
        print(f"Error in validate-list: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/search-exams")
async def search_exams(request: Request):
    """Busca manual no BigQuery."""
    try:
        from core.bigquery_client import bq_client
        data = await request.json()
        term = data.get("term", "")
        unit = data.get("unit", "Goiânia Centro")
        
        if len(term) < 2:
            return {"exams": []}
            
        results = bq_client.search_exams(term, unit)
        return {"exams": results}
    except Exception as e:
        print(f"Error in search-exams: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/learn-correction")
async def learn_correction(request: Request):
    """Registra aprendizado do sistema (Learning System)."""
    try:
        from services.learning_service import learning_service
        data = await request.json()
        original = data.get("original_term")
        correct = data.get("correct_exam_name")
        
        if original and correct:
            # V90: Match new signature 'learn(original_term, correct_exam_name)'
            learning_service.learn(original, correct)
            return {"status": "learned"}
        return {"status": "ignored"}
    except Exception as e:
        print(f"Error in learn-correction: {e}")
        return {"status": "error", "detail": str(e)}

@app.get("/api/pdca/logs")
async def get_pdca_logs():
    """Retorna logs do sistema de aprendizado para o Admin Dashboard."""
    try:
        from services.pdca_service import pdca_service
        # V90: pdca_service.logs is the list itself
        return pdca_service.logs
    except Exception as e:
        print(f"Error getting PDCA logs: {e}")
        return []

@app.post("/api/pdca/approve")
async def approve_pdca(request: Request):
    """Aprova um ajuste de PDCA."""
    try:
        from services.pdca_service import pdca_service
        data = await request.json()
        term = data.get("term")
        unit = data.get("unit")
        
        if pdca_service.approve_action(term, unit):
            return {"status": "approved"}
        return {"status": "not_found"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Catch-All for /api
@app.api_route("/api/{path_name:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def catch_all(path_name: str):
    return {
        "error": "Not Found",
        "path": path_name,
        "message": f"Endpoint '/api/{path_name}' not specifically handled in V90.0. Check index.py routes."
    }
