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

@app.post("/api/search-exams")
@app.post("/search-exams")
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
        print(f"❌ Error in search-exams wrapper: {e}")
        raise HTTPException(status_code=500, detail=str(e))
