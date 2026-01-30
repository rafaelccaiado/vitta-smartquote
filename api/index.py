from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Vitta SmartQuote Infra Probe (V74.0)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
async def health():
    return {"status": "ok", "probe": "V74.0 - FULL FRONTEND TEST"}

@app.get("/api/qa-proof")
async def qa_proof():
    return {"status": "ok", "version": "V74.0"}
