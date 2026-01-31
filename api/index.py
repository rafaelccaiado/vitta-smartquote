from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import sys

# Standardize python path
base_dir = os.path.dirname(os.path.abspath(__file__))
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

@app.get("/api/health")
async def health():
    return {
        "status": "online",
        "version": "V86.0 Split",
        "function": "Health/Index"
    }

@app.get("/api/qa-proof")
async def qa_proof():
    return {"status": "ok", "diagnostics": "V86.0 Split Mode"}

@app.get("/api")
async def root_api():
    return await health()
