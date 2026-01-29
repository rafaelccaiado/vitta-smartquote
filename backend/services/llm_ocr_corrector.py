import google.generativeai as genai
import json
import os
from typing import List, Dict, Optional
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

class LLMOCRCorrector:
    """
    Corretor de erros de OCR usando LLM (Gemini).
    Especializado em pedidos médicos brasileiros.
    """
    
    def __init__(self):
        # Configurar Gemini
        api_key = os.getenv("GEMINI_API_KEY")
        
        if not api_key:
            print("⚠️ GEMINI_API_KEY não configurada - correção LLM desabilitada")
            print("   Configure a variável de ambiente para ativar correção automática")
            self.model = None
            self.correction_cache = {}
            return
        
        try:
            genai.configure(api_key=api_key)
            
            # Usar Gemini Flash (mais rápido e barato)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
            
            # Cache de correções comuns (para economizar chamadas)
            self.correction_cache = {}
            
            print("✅ LLM OCR Corrector inicializado com Gemini Flash")
        except Exception as e:
            print(f"⚠️ Erro ao inicializar Gemini: {e}")
            self.model = None
            self.correction_cache = {}
    
    def correct_ocr_text(self, ocr_text: str) -> Dict[str, any]:
        """
        Corrige erros de OCR usando contexto médico.
        
        Args:
            ocr_text: Texto bruto extraído pelo OCR
            
        Returns:
            {
                "original": texto original,
                "corrected_terms": [
                    {"ocr": "Homorama", "corrected": "Hemograma", "confidence": 0.95},
                    ...
                ],
                "raw_response": resposta completa do LLM
            }
        """
        # Se modelo não disponível, retornar texto original
        if not self.model:
            return {
                "original": ocr_text,
                "corrected_terms": [],
                "error": "LLM não disponível (GEMINI_API_KEY não configurada)"
            }
        
        # Verificar cache
        cache_key = ocr_text.strip().lower()
        if cache_key in self.correction_cache:
            return self.correction_cache[cache_key]
        
        # Criar prompt especializado
        prompt = self._build_correction_prompt(ocr_text)
        
        try:
            # Chamar Gemini
            response = self.model.generate_content(prompt)
            
            # Parsear resposta JSON
            result = self._parse_llm_response(response.text, ocr_text)
            
            # Cachear resultado
            self.correction_cache[cache_key] = result
            
            return result
            
        except Exception as e:
            print(f"⚠️ Erro ao corrigir OCR com LLM: {e}")
            # Fallback: retornar texto original sem correção
            return {
                "original": ocr_text,
                "corrected_terms": [],
                "error": str(e)
            }
    
    def _build_correction_prompt(self, ocr_text: str) -> str:
        """Constrói prompt otimizado para correção de exames médicos"""
        
        return f"""Você é um especialista em extração de EXAMES LABORATORIAIS de pedidos médicos.
Sua função é identificar APENAS nomes de exames e corrigir erros de digitação (OCR).

O OCR extraiu este texto bruto:
```
{{ocr_text}}
```

REGRAS CRÍTICAS (ANTI-ALUCINAÇÃO):
1. IGNORE TUDO que não for nome de exame.
   - Nomes de pacientes, Médicos (Dr.), CRM, Datas, Idades (35a, 2m), Gênero (Masculino/Feminino).
   - Cabeçalhos (Solicitação, Pedido, Laboratório).
   - Especialidades médicas (Urologia, Cardiologia, Ginecologia) -> NÃO CONVERTA 'Urologia' em 'Ureia'.
   - Endereços e telefones.
   
2. NÃO INVENTE EXAMES.
   - Se o OCR leu "Estradiol", mantenha "Estradiol". NÃO troque por "Colesterol" ou "Lipidograma".
   - Se o texto é "Urologia", IGNORE.
   - Se o texto é "35a 9m", IGNORE.

3. CORRIJA ERROS REAIS DE OCR:
   - "Hemoglama" -> "Hemograma"
   - "Gicose" -> "Glicose"
   - "T4 Lvre" -> "T4 Livre"

SAÍDA OBRIGATÓRIA (JSON):
{{
  "exames": [
    {{"ocr": "texto_original_do_ocr", "corrected": "nome_do_exame_corrigido", "confidence": 0.95}},
    ...
  ]
}}

EXEMPLOS DE FILTRAGEM:
Entrada: "Dr. Joao Silva" -> SAÍDA: Ignorar
Entrada: "35 anos" -> SAÍDA: Ignorar
Entrada: "Urologia" -> SAÍDA: Ignorar
Entrada: "Hemograma Completo" -> SAÍDA: {{"ocr": "Hemograma Completo", "corrected": "Hemograma Completo", "confidence": 1.0}}

IMPORTANTE: Retorne APENAS o JSON válido. Se não houver exames, retorne {{"exames": []}}.
"""
    
    def _parse_llm_response(self, response_text: str, original_text: str) -> Dict:
        """Parseia resposta do LLM e extrai JSON"""
        
        try:
            # Tentar extrair JSON da resposta
            # O LLM pode retornar com markdown ```json ... ```
            json_text = response_text.strip()
            
            # Remover markdown se presente
            if json_text.startswith("```"):
                lines = json_text.split("\n")
                json_text = "\n".join(lines[1:-1])  # Remove primeira e última linha
            
            # Parsear JSON
            parsed = json.loads(json_text)
            
            # Validar estrutura
            if "exames" not in parsed:
                raise ValueError("Resposta não contém campo 'exames'")
            
            return {
                "original": original_text,
                "corrected_terms": parsed["exames"],
                "raw_response": response_text
            }
            
        except json.JSONDecodeError as e:
            print(f"⚠️ Erro ao parsear JSON do LLM: {e}")
            print(f"Resposta: {response_text}")
            
            # Fallback: tentar extrair termos manualmente
            return {
                "original": original_text,
                "corrected_terms": [],
                "error": f"JSON inválido: {str(e)}",
                "raw_response": response_text
            }
    
    def get_corrected_list(self, ocr_text: str) -> List[str]:
        """
        Versão simplificada que retorna apenas lista de termos corrigidos.
        
        Args:
            ocr_text: Texto do OCR
            
        Returns:
            Lista de termos corrigidos
        """
        result = self.correct_ocr_text(ocr_text)
        
        if "corrected_terms" in result and result["corrected_terms"]:
            # Retornar apenas termos com confiança > 0.5
            return [
                term["corrected"] 
                for term in result["corrected_terms"]
                if term.get("confidence", 0) > 0.5
            ]
        
        # Fallback: retornar linhas do texto original
        return [line.strip() for line in ocr_text.split("\n") if line.strip()]

# Singleton
llm_ocr_corrector = LLMOCRCorrector()
