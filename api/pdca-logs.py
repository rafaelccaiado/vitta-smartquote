from fastapi import FastAPI
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

@app.get("/api/pdca/logs")
@app.get("/pdca/logs")
async def get_pdca_logs():
    """Retorna logs do sistema de aprendizado para o Admin Dashboard."""
    try:
        from services.learning_service import learning_service
        logs = getattr(learning_service, "get_all_logs", lambda: [])()
        return logs
    except Exception as e:
        return []
