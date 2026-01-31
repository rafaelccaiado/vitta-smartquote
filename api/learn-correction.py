from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import os
import sys

# Standardize python path for Vercel
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

@app.post("/api/learn-correction")
@app.post("/learn-correction")
async def learn_correction(request: Request):
    """Registra aprendizado do sistema (Learning System)."""
    try:
        from services.learning_service import learning_service
        data = await request.json()
        original = data.get("original_term")
        correct = data.get("correct_exam_name")
        
        if original and correct:
            learning_service.add_mapping(original, correct)
            return {"status": "learned"}
        return {"status": "ignored"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
