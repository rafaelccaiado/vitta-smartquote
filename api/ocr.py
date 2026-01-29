from fastapi import FastAPI, UploadFile, File, Response
import os
import sys

# 1. Configurar Path para Imports (CRUCIAL para Vercel)
# Adiciona o diretório atual ao path para poder importar ocr_processor.py local
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 2. Inicialização Segura da App
app = FastAPI()

# 3. Import Explícito do Pipeline V81.1
pipeline_ready = False
OCRProcessor = None
try:
    from ocr_processor import OCRProcessor
    pipeline_ready = True
except ImportError as e:
    print(f"❌ Erro Crítico de Importação: {e}")
except Exception as e:
    print(f"❌ Erro Desconhecido na Importação: {e}")

# Global singleton para reuso em ambiente serverless (Cold Start Optimization)
_processor_instance = None

def get_processor():
    global _processor_instance
    if _processor_instance is None and OCRProcessor:
        try:
            _processor_instance = OCRProcessor()
        except Exception as e:
            print(f"❌ Erro de Inicialização da Classe: {e}")
            return None
    return _processor_instance

# 4. ENTRYPOINT DA ROTA (Seguindo Regra Vercel: Rota "/")
@app.post("/")
async def ocr_entrypoint(response: Response, file: UploadFile = File(...), unit: str = "Goiânia Centro"):
    # A) Anti-Cache Headers Reais (No RESPONSE)
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    
    # B) Diagnóstico de Versão
    BACKEND_VERSION = "V81.1-Fallback-System"
    
    # C) Checagem de Inicialização
    processor = get_processor()
    if not processor:
        return {
            "error": "OCR Processor Init Failed (api/ocr.py)",
            "backend_version": BACKEND_VERSION,
            "debug_meta": {
                "dictionary_loaded": False,
                "dictionary_size": 0,
                "raw_ocr_lines": 0,
                "fallback_used": False,
                "error": "Module Import or Class Init Failed"
            }
        }

    # D) Leitura do Arquivo
    try:
        contents = await file.read()
    except Exception as e:
        return {"error": f"File Read Error: {str(e)}"}

    # E) Execução do Pipeline
    result = processor.process_image(contents)

    # F) GARANTIA DE OBSERVABILIDADE & FALLBACK
    # Se o output do processor não tiver os metadados, injetamos aqui
    if "backend_version" not in result:
        result["backend_version"] = BACKEND_VERSION
    
    # G) FALLBACK DE EMERGÊNCIA (Caso o processador retorne vazio mas tenha lido algo)
    stats = result.get("stats", {})
    total_ocr = stats.get("total_ocr_lines", 0)
    lines = result.get("lines", [])
    
    # Se tem texto bruto, mas lista veio vazia -> FORÇAR TEXTO ORIGINAL
    if total_ocr > 0 and not lines:
        # Tenta recuperar do debug_raw se disponível, senão avisa
        debug_raw = result.get("debug_raw", [])
        if debug_raw:
             # Converter debug_raw strings em objetos line
            fallback_lines = []
            for text in debug_raw:
                 fallback_lines.append({
                    "original": text,
                    "corrected": f"[⚠️ Não Verificado] {text}",
                    "confidence": 0.1,
                    "method": "emergency_fallback"
                })
            result["lines"] = fallback_lines
            result["text"] = "\n".join([l["corrected"] for l in fallback_lines])
            result["debug_meta"] = result.get("debug_meta", {})
            result["debug_meta"]["fallback_used"] = True
            result["backend_version"] = f"{BACKEND_VERSION} (Emergency Fallback)"

    return result
