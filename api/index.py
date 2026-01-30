from fastapi import FastAPI
import os

app = FastAPI()

@app.get("/api/health")
async def health():
    return {"status": "debug_v1", "msg": "Infrastructure is OK"}

@app.get("/api/qa-proof")
async def qa_proof():
    return {"status": "debug_v1", "build": "INFRA-TEST"}
