from typing import List, Dict, Any

class OCRResoluteAuditor:
    """
    Auditor independente para validar a cobertura e precisão do OCR.
    Vitta Resolute Pipeline layer.
    """
    def __init__(self):
        pass

    def audit(self, raw_lines: List[str], matched_exams: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Gera métricas de confiança e identifica possíveis exames perdidos.
        """
        total_raw = len(raw_lines)
        total_matched = len(matched_exams)
        
        # Filtra linhas que parecem exames mas não foram pareadas
        potential_misses = []
        for line in raw_lines:
            if self._looks_like_exam(line):
                # Verifica se esta linha (ou similar) está no matched_exams
                if not any(m['original'] == line for m in matched_exams):
                    potential_misses.append(line)

        score = 100.0
        if total_raw > 0:
            # Penaliza por cada possível perda
            penalty = (len(potential_misses) / max(1, total_raw)) * 50
            score = max(0, 100 - penalty)

        return {
            "resolute_score": round(score, 1),
            "potential_misses": potential_misses[:5],
            "total_raw": total_raw,
            "total_matched": total_matched,
            "audit_version": "V1.0"
        }

    def _looks_like_exam(self, text: str) -> bool:
        """Heurística simples para identificar linhas que poderiam ser exames."""
        text = text.upper()
        # Se tem muitos números ou caracteres especiais de data/crm, não é exame
        if any(x in text for x in ["CRM", "DATA", "TELEFONE", "ENDERECO", "RUA"]):
            return False
        # Exames geralmente têm entre 3 e 40 caracteres
        if 3 <= len(text) <= 40:
            return True
        return False

ocr_resolute_auditor = OCRResoluteAuditor()
