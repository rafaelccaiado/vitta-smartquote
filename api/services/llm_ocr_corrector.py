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
        
        return f"""Você é um especialista em pedidos médicos laboratoriais brasileiros.

O OCR extraiu este texto de um pedido manuscrito:

```
{ocr_text}
```

TAREFA:
1. Identifique termos que parecem ser nomes de exames laboratoriais
2. Ignore termos que NÃO são exames, como:
    - Diagnósticos (CID, HDS, HD)
    - Números aleatórios ou códigos internos
    - Logotipos ("Hosp", "Denmar", "Unimed")

3.  **SEPARE EXAMES AGRUPADOS**:
    - Se uma linha tiver múltiplos exames, quebre em itens separados.
    - Ex: "Ureia, Creatinina" -> ["Ureia", "Creatinina"]
    - Ex: "Complemento C3, C4" -> ["Complemento C3", "Complemento C4"]
    - Ex: "TGO / TGP" -> ["TGO", "TGP"]

4.  **EXPANDA ANTICORPOS (IgG/IgM/IgA)**:
    - Se houver múltiplos anticorpos na mesma linha, crie exames separados PRESERVANDO o nome base.
    - Ex: "Anti Beta 2 Glicoproteina IgM IgG" -> ["Anti Beta 2 Glicoproteina IgM", "Anti Beta 2 Glicoproteina IgG"]
    - Ex: "Sorologia Dengue IgG e IgM" -> ["Dengue IgG", "Dengue IgM"]

5.  **IDENTIFIQUE** os exames laboratoriais válidos.
    - Inclua **Autoanticorpos**: FAN, Anti-DNA, Anti-SM, Anti-RO, Anti-LA, Anti-RNP, ANCA.

6.  **CORRIJA** erros de OCR nos exames identificados:
    - Contexto médico brasileiro (ex: "Hemograma", "TSH", "EAS")
    - Corrija siglas e erros de digitação (ex: "Homograma" -> "Hemograma")

7. Para cada termo identificado e corrigido, retorne:
   - O texto original do OCR
   - A correção sugerida
   - Nível de confiança (0.0 a 1.0)

EXAMES COMUNS NO BRASIL:
- Hemograma, Lipidograma, Colesterol (total/HDL/LDL)
- TSH, T3, T4 Livre, FSH, LH
- Glicemia, Glicose, Hemoglobina Glicada
- Ureia, Creatinina, Ácido Úrico
- TGO, TGP, Gama GT
- EAS (Urina Tipo I), Parasitológico de Fezes
- PSA, Beta HCG
- Vitamina D, Vitamina B12, Ferritina

FORMATO DE SAÍDA (JSON):
{{
  "exames": [
    {{"ocr": "texto_original", "corrected": "texto_corrigido", "confidence": 0.95}},
    ...
  ]
}}

IMPORTANTE:
- Retorne APENAS o JSON, sem texto adicional
- Se não tiver certeza, mantenha o texto original
- Ignore linhas que não parecem exames (nomes, datas, etc)
- Confiança alta (>0.9) apenas para correções óbvias
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
