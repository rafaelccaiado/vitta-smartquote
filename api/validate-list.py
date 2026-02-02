from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import os
import sys
import traceback

# Standardize python path for Vercel
base_dir = os.path.dirname(os.path.abspath(__file__)) # /api
if base_dir not in sys.path:
    sys.path.append(base_dir)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/validate-list")
@app.post("/validate-list")
async def validate_list(request: Request):
    """Valida uma lista de termos de exames (Phase 4/5)."""
    try:
        from core.validation_logic import ValidationService
        from core.bigquery_client import bq_client
        
        data = await request.json()
        terms = data.get("terms", [])
        unit = data.get("unit", "Goiânia Centro")
        
        # Call consolidated logic
        results_data = ValidationService.validate_batch(terms, unit, bq_client)
            
        return results_data
    except Exception as e:
        print(f"❌ Error in validate-list wrapper: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
