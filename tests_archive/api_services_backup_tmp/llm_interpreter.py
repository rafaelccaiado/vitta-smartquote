import json
import os
import requests
from typing import List, Dict, Optional
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

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
1. Identifique APENAS os exames laboratoriais citados.
2. Corrija erros óbvios de OCR (ex: "hmgrama" -> "Hemograma", "Gicose" -> "Glicose").
3. Normalize siglas (ex: "T4L" -> "T4 Livre", "HbA1c" -> "Hemoglobina Glicada").

REGRAS DE OURO (NOISE FIREWALL):
❌ PROIBIDO RETORNAR ENDEREÇOS: Ignore "Rua", "Av", "Alameda", "Setor", "Quadra", "Lote".
❌ PROIBIDO RETORNAR CIDADES: Ignore "Goiânia", "Brasília", "Aparecida", "Valparaíso".
❌ PROIBIDO RETORNAR MÉDICOS: Ignore nomes de pessoas, "Dr.", "Dra.", "CRM".
❌ PROIBIDO RETORNAR METADADOS: Ignore "Página", "Folha", "Impresso em", "Data", "Telefone".

✅ EXEMPLOS DE EXAMES VÁLIDOS (SALVAGUARDA):
Se o texto for "ANTI GLIADINA", "TSH", "HEMOGRAMA", "UREIA" -> SÃO EXAMES, MANTENHA.

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
Responda APENAS o JSON. Se não houver exames, retorne {{"exames": []}}."""

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
    def classify_lines(self, lines: List[str]) -> List[Dict[str, any]]:
        """
        Classifica cada linha em categorias (EXAME, MEDICO, etc)
        """
        if not self.api_key:
            return []

        prompt = f"""Classifique cada linha em UMA categoria:

CATEGORIAS:
- EXAME: nome de exame laboratorial
- MEDICO: nome/CRM de médico
- ENDERECO: rua, cidade, CEP, referência
- PACIENTE: nome, CPF, convênio do paciente
- METADATA: data, assinatura, carimbo
- LIXO: texto ilegível ou irrelevante

LINHAS PARA CLASSIFICAR:
{json.dumps(lines, indent=2, ensure_ascii=False)}

RESPONDA APENAS JSON neste formato:
[
  {{"linha": "texto original", "categoria": "CATEGORIA", "confianca": 0.0 a 1.0}}
]"""

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"response_mime_type": "application/json"}
        }
        
        try:
            response = requests.post(self.url, json=payload, timeout=30)
            response.raise_for_status()
            data = response.json()
            content = data['candidates'][0]['content']['parts'][0]['text']
            return json.loads(content)
        except Exception as e:
            print(f"❌ Erro na classificação LLM: {e}")
            return []

# Singleton
llm_interpreter = LLMInterpreter()
