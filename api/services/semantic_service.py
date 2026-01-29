# import google.generativeai as genai
import os
import json
import re
from dotenv import load_dotenv

load_dotenv()

class SemanticService:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if self.api_key:
            try:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel('gemini-1.5-flash')
                print("✅ SemanticService: Model Initialized")
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
        You are a medical billing expert specialized in Brazilian TUSS/CBHPM coding.
        
        Task: Normalize these raw text strings (from OCR/Handwriting) into the exact standard TUSS/CBHPM exam name.
        
        Examples:
        - Input: "Ac. Anti-TPO" -> Output: "Anti-Tireoperoxidase"
        - Input: "TGO / TGP" -> Output: "TGO" (Split items should be handled by caller, but if stuck, map to first main exam)
        - Input: "EAS" -> Output: "Urina Tipo I"
        - Input: "H. Pylori" -> Output: "Pesquisa de Helicobacter Pylori"
        - Input: "Vit D" -> Output: "25 Hidroxivitamina D"
        - Input: "TSH Ultra" -> Output: "Hormonio Tireoestimulante"
        - Input: "Glicemia Jejum" -> Output: "Glicose"
        
        Rules:
        1. Return ONLY valid JSON format {{ "original": "standard_name" }}.
        2. IF the term refers to a specific antibody (IgG/IgM), INCLUDE it in the name.
        3. Correct typos (e.g., "Hemagroma" -> "Hemograma").
        4. Expand abbreviations.
        
        Input Terms:
        {json.dumps(valid_terms, ensure_ascii=False)}

        JSON Output:
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
