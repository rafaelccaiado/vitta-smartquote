# import google.generativeai as genai
import os
import json
import re
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

class SemanticService:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if self.api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel('gemini-1.5-flash')
                print("✅ SemanticService: Model Initialized (Gemini 1.5 Flash)")
            except Exception as e:
                 print(f"⚠️ SemanticService Init Error: {e}")
                 self.model = None
        else:
            print("⚠️ SemanticService: GEMINI_API_KEY not found in environment.")
            self.model = None

    def normalize_batch(self, terms):
        """
        Uses Gemini to normalize a list of medical terms to their standard technical names.
        Returns a dict: { "original_term": "normalized_term" }
        """
        if not self.model or not terms:
            return {}

        # Filter out very short terms to save tokens/time
        valid_terms = [t for t in terms if len(t) > 3]
        if not valid_terms:
            return {}

        prompt = f"""
        Você é um especialista em codificação médica brasileira (TUSS, LOINC).
        Converta o termo de exame abaixo para o nome oficial e completo mais provável encontrado em catálogos de laboratórios (Ex: Sabin, Fleury, Hermes Pardini).
        
        REGRAS CRÍTICAS:
        1. Retorne APENAS um JSON plano: {{ "original": "Nome Completo do Exame" }}.
        2. Priorize nomes que incluam a metodologia se implícito (Ex: "Glicada" -> "Hemoglobina Glicada (A1C)").
        3. Se for uma sigla comum, retorne o nome por extenso + sigla (Ex: "TGO" -> "TGO (AST) - Transaminase Oxalacetica").
        4. Se o termo parecer um código numérico TUSS (ex: 40301230), mapeie para o nome do exame correspondente.
        5. Remova ruídos de OCR (datas, CRM, nomes de médicos, "solicito", "exames").
        6. Se houver múltiplos exames (ex: "TGO/TGP"), retorne apenas o primeiro no valor, pois o orquestrador tratará a divisão.

        Termos de Entrada:
        {json.dumps(valid_terms, ensure_ascii=False)}

        Resposta JSON:
        """

        try:
            response = self.model.generate_content(prompt)
            text = response.text
            # Clean possible markdown code blocks
            text = re.sub(r"```json|```", "", text).strip()
            
            mapping = json.loads(text)
            return mapping
        except Exception as e:
            print(f"❌ SemanticService Error: {e}")
            return {}
            
semantic_service = SemanticService()
