import os
import sys

# Adicionar o diretório raiz ao PYTHONPATH para encontrar o backend
# Vercel geralmente roda a partir da raiz, mas para garantir:
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

# Agora importar o app real
try:
    from backend.main import app
except ImportError as e:
    # Fallback para debug se a importação falhar
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    app = FastAPI()
    
    @app.get("/api/{path:path}")
    def fallback(path: str):
        return JSONResponse(
            status_code=500,
            content={
                "error": "Failed to import backend application",
                "detail": str(e),
                "cwd": os.getcwd(),
                "sys_path": sys.path
            }
        )
