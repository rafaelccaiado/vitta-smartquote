import json
import os
from datetime import datetime
from typing import List, Dict, Any

class PDCAService:
    """
    Advanced PDCA Debugging Service using FCA (Fato, Causa, Ação) methodology.
    Aims to automate system improvements by classifying validation failures.
    """
    def __init__(self, log_file="pdca_fca_logs.json"):
        if os.getenv("VERCEL") or os.getenv("ENVIRONMENT") == "production":
            self.log_file = os.path.join("/tmp", log_file)
        else:
            self.log_file = os.path.join("logs", log_file)
            os.makedirs("logs", exist_ok=True)
            
        self.logs = self._load_logs()

    def _load_logs(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.log_file):
            return []
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []

    def _save_logs(self):
        try:
            with open(self.log_file, 'w', encoding='utf-8') as f:
                json.dump(self.logs, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ PDCA Error saving logs: {e}")

    def log_fca(self, term: str, unit: str, status: str, strategy: str = "none", matches: List[Any] = None):
        """
        Classifies a validation event into Fact, Cause, and Action.
        """
        if status == "confirmed":
            return # Don't log success unless requested

        fact = f"Termo '{term}' resultou em status '{status}' na unidade '{unit}'"
        cause = "Desconhecida"
        action = "Verificar manualmente"
        confidence = 0.5

        # Heuristic classification of cause
        from services.fuzzy_matcher import fuzzy_matcher
        best_match = fuzzy_matcher.find_best_match(term, min_score=60)
        if not matches or len(matches) == 0:
            if best_match:
                cause = f"Sinônimo Faltante: Fuzzy encontrou '{best_match['match']}' com score {best_match['score']}"
                action = f"Adicionar sinônimo: '{term}' -> '{best_match['match']}'"
                confidence = best_match['score'] / 100.0
            else:
                cause = "Exame não encontrado no catálogo (Possível termo novo ou erro OCR crítico)"
                action = "Revisar termo original e verificar se o exame deve ser incluído no sistema ou corrigido no OCR"
                confidence = 0.3
        elif status == "multiple":
            cause = "Ambiguidade: Múltiplos matches encontrados"
            action = "Refinar critérios de desempate ou material"
            confidence = 0.6

        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "term": term,
            "unit": unit,
            "fato": fact,
            "causa": cause,
            "acao": action,
            "confidence": confidence,
            "status": "pending_admin_approval",
            "matches_count": len(matches) if matches else 0
        }

        # Avoid duplicates in the same session/unit
        if not any(l["term"] == term and l["unit"] == unit and l["status"] == "pending_admin_approval" for l in self.logs[-50:]):
            self.logs.append(log_entry)
            self._save_logs()
            print(f"📊 PDCA/FCA Logged: {term} -> {cause}")

    def get_pending_actions(self) -> List[Dict[str, Any]]:
        return [l for l in self.logs if l["status"] == "pending_admin_approval"]

    def approve_action(self, term: str, unit: str):
        for log in self.logs:
            if log["term"] == term and log["unit"] == unit and log["status"] == "pending_admin_approval":
                log["status"] = "approved_and_executed"
                # Here we could trigger learning_service.learn()
                self._save_logs()
                return True
        return False

pdca_service = PDCAService()
