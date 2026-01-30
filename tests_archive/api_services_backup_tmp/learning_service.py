import json
import os
from typing import Dict

class LearningService:
    def __init__(self, file_path="learned_mappings.json"):
        self.file_path = file_path
        self.mappings = self._load_mappings()

    def _load_mappings(self) -> Dict[str, str]:
        if not os.path.exists(self.file_path):
            return {}
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Erro ao carregar mappings: {e}")
            return {}

    def save_mappings(self):
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(self.mappings, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Erro ao salvar mappings: {e}")

    def learn(self, original_term: str, correct_exam_name: str):
        """
        Aprende que 'original_term' deve ser mapeado para 'correct_exam_name'
        Ex: 'TGO' -> 'ASPARTATO AMINOTRANSFERASE (AST)'
        """
        key = original_term.strip().lower()
        self.mappings[key] = correct_exam_name
        self.save_mappings()
        print(f"🧠 Aprendido: '{original_term}' -> '{correct_exam_name}'")

    def get_learned_match(self, term: str) -> str:
        key = term.strip().lower()
        return self.mappings.get(key)

learning_service = LearningService()
