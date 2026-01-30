from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()

@app.get("/")
def qa_proof():
    return JSONResponse({
        "build_id": "PROD-QA-RUNNER-20260129-2255",
        "status": "ok"
    })
