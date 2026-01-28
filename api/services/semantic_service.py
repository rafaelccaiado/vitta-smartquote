import google.generativeai as genai
import os
import json
import re

class SemanticService:
    def __init__(self):
        self.api_key = os.getenv("GEMINI_API_KEY")
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
        else:
            print("⚠️ SemanticService: GEMINI_API_KEY not found.")
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
        You are a medical billing expert acting as a normalizer.
        Task: Convert these handwritten/abbreviated exam names into their standard TUSS/CBHPM nomenclature (technical name).
        
        Rules:
        1. Return ONLY valid JSON format {{ "original": "standard_name" }}.
        2. If a term is already correct or unrecognized, map it to itself or null.
        3. Do not add explanations.
        4. Focus on Brazilian Portuguese medical terminology.

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
