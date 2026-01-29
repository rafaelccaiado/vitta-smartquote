import os
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
import uvicorn
import shutil

# Importar processadores reais
ocr_processor = None
bq_client = None
ValidationService = None
learning_service = None

try:
    from ocr_processor import OCRProcessor
    from bigquery_client import BigQueryClient
    from validation_logic import ValidationService
    from services.learning_service import learning_service
except Exception as e:
    print(f"⚠️ Erro ao importar dependências: {e}")

app = FastAPI(title="Vittá SmartQuote API")

# Inicializar clientes
try:
    print("⏳ Inicializando clientes...")
    if 'OCRProcessor' in globals() and OCRProcessor:
        ocr_processor = OCRProcessor()
    if 'BigQueryClient' in globals() and BigQueryClient:
        bq_client = BigQueryClient()
    print("✅ Clientes inicializados")
except Exception as e:
    print(f"❌ Erro crítico na inicialização: {e}")

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
def health_check():
    return {
        "status": "online",
        "ocr_initialized": ocr_processor is not None,
        "bq_initialized": bq_client is not None,
        "gemini_api_key": "Configurada" if os.getenv("GEMINI_API_KEY") else "AUSENTE",
        "gcp_key": "Configurada" if os.getenv("GCP_SA_KEY_BASE64") else "AUSENTE"
    }

@app.get("/")
def read_root():
    return {"status": "online", "service": "Vittá SmartQuote API"}

@app.get("/api/units")
async def get_units():
    try:
        units = bq_client.get_units()
        return {"units": units}
    except Exception as e:
        print(f"Erro ao buscar unidades: {e}")
        # Fallback se der erro no BQ para não travar o front
        return {"units": ["Goiânia Centro", "Anápolis", "Trindade"]}

@app.post("/api/ocr")
async def process_ocr(file: UploadFile = File(...), unit: str = "Goiânia Centro"):
    try:
        # Ler arquivo enviado
        contents = await file.read()
        
        # Processar com OCR real
        if not ocr_processor:
             return {"error": "OCR Processor não inicializado no servidor. Verifique logs e chaves GCP."}
             
        result = ocr_processor.process_image(contents)
        
        if "error" in result:
             raise HTTPException(status_code=500, detail=result["error"])
             
        return result
        
    except Exception as e:
        print(f"Erro no endpoint OCR: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/search-exams")
async def search_exams_endpoint(data: dict):
    # Recebe { "term": "...", "unit": "..." }
    try:
        term = data.get("term", "")
        unit = data.get("unit", "Goiânia Centro")
        
        if not term:
            return {"exams": []}
            
        # Busca no BigQuery
        exams = bq_client.search_exams(term, unit)
        
        # Formatar resposta
        return {
            "exams": exams,
            "count": len(exams)
        }
            
    except Exception as e:
        print(f"Erro na busca: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/validate-list")
async def validate_list(data: dict):
    # Recebe { "terms": ["hemograma", ...], "unit": "..." }
    try:
        terms = data.get("terms", [])
        unit = data.get("unit", "Goiânia Centro")
        
        print(f"Validando {len(terms)} termos para unidade {unit}")
        
        # Usar o validation service com o cliente BQ
        # Nota: ValidationService.validate_batch agora espera o cliente bq para fazer as buscas
        result = ValidationService.validate_batch(terms, unit, bq_client)
        
        return result
        
    except Exception as e:
        print(f"Erro na validação em lote: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/learn-correction")
async def learn_correction(data: dict):
    # Recebe { "original_term": "TGO", "correct_exam_name": "ASPARTATO..." }
    try:
        original = data.get("original_term")
        correct = data.get("correct_exam_name")
        
        if original and correct:
            learning_service.learn(original, correct)
            return {"status": "success", "message": f"Learned: {original} -> {correct}"}
        
        return {"status": "ignored"}
    except Exception as e:
        print(f"Erro learning: {e}")
        # Não falhar request por isso
        return {"status": "error"}

@app.get("/api/curation-report")
async def get_curation_report():
    """
    Gera relatório de curadoria com:
    - Exames não encontrados (para adicionar na tabela de preços)
    - Sugestões de sinônimos (para melhorar matching)
    """
    try:
        from services.missing_terms_logger import missing_terms_logger
        
        # Gera relatório em markdown
        report_content = missing_terms_logger.generate_report()
        
        # Também exporta para arquivo
        report_file = missing_terms_logger.export_report()
        
        return {
            "report": report_content,
            "file_path": report_file,
            "not_found_count": len([t for t in missing_terms_logger.not_found_terms.values() 
                                   if t["status"] == "pending"]),
            "synonym_suggestions_count": len([s for s in missing_terms_logger.fuzzy_matches.values() 
                                             if s["status"] == "pending"])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
