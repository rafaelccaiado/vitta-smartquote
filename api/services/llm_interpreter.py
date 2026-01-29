import json
import os
import requests
from typing import List, Dict, Optional
from dotenv import load_dotenv

load_dotenv()

class LLMInterpreter:
    """
    Interpreta texto OCR usando Gemini API via REST (sem SDK pesado).
    Especializado em extração estruturada de exames.
    """
    
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        self.url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"
        
        if not self.api_key:
            print("⚠️ GEMINI_API_KEY não configurada - LLM Interpreter desativado")
            
    def extract_exams(self, ocr_text: str) -> Dict[str, any]:
        """
        Extrai e normaliza exames do texto bruto.
        """
        if not self.api_key:
            return {"exames": [], "error": "API Key missing"}
            
        prompt = f"""Você é um especialista em pedidos médicos brasileiros. Analise o texto OCR abaixo.

TAREFA:
1. Identifique TODOS os exames laboratoriais citados.
2. Corrija erros óbvios de OCR (ex: "hmgrama" -> "Hemograma").
3. Normalize siglas (ex: "T4L" -> "T4 Livre", "HbA1c" -> "Hemoglobina Glicada").
4. Ignore nomes de pacientes, médicos, endereços, logotipos e metadados.

TEXTO OCR:
\"\"\"
{ocr_text}
\"\"\"

Siga RIGOROSAMENTE este formato JSON:
{{
  "exames": [
    {{
      "texto_original": "como veio do OCR",
      "exame_identificado": "Nome padronizado",
      "confianca": 0.0 a 1.0
    }}
  ]
}}
Responda APENAS o JSON."""

        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "response_mime_type": "application/json"
            }
        }
        
        try:
            response = requests.post(self.url, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            # Extrair o texto da resposta do Gemini
            content = data['candidates'][0]['content']['parts'][0]['text']
            return json.loads(content)
            
        except Exception as e:
            print(f"❌ Erro no LLM Interpreter: {e}")
            return {"exames": [], "error": str(e)}

# Singleton
llm_interpreter = LLMInterpreter()
