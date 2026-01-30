from typing import List, Dict, Tuple, Optional, Any
from difflib import SequenceMatcher, get_close_matches

class FuzzyMatcher:
    """
    Matching inteligente de termos usando algoritmos de similaridade nativos (difflib).
    Substitui rapidfuzz para evitar dependências pesadas no Vercel.
    """
    
    def __init__(self, known_exams: List[str] = None):
        self.known_exams = known_exams or []
        self._normalized_exams = {}
        if self.known_exams:
            self._build_normalized_map()
    
    def _build_normalized_map(self):
        for exam in self.known_exams:
            normalized = self._normalize(exam)
            self._normalized_exams[normalized] = exam
    
    def _normalize(self, text: str) -> str:
        import unicodedata
        text = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('ASCII')
        return text.lower().strip()
    
    def update_known_exams(self, exams: List[str]):
        self.known_exams = exams
        self._build_normalized_map()
    
    def find_best_match(
        self, 
        term: str, 
        min_score: int = 50
    ) -> Optional[Dict[str, Any]]:
        if not self.known_exams:
            return None
        
        normalized_term = self._normalize(term)
        
        # Usa difflib get_close_matches para encontrar o melhor candidato
        matches = get_close_matches(normalized_term, self._normalized_exams.keys(), n=1, cutoff=min_score/100.0)
        
        if not matches:
            return None
        
        matched_normalized = matches[0]
        matched_exam = self._normalized_exams[matched_normalized]
        
        # Calcula score real usando SequenceMatcher
        score = int(SequenceMatcher(None, normalized_term, matched_normalized).ratio() * 100)
        
        if score < min_score:
            return None

        # Classificar confiança
        if score >= 85:
            confidence = "high"
        elif score >= 70:
            confidence = "medium"
        else:
            confidence = "low"
        
        return {
            "term": term,
            "match": matched_exam,
            "score": score,
            "confidence": confidence,
            "normalized_term": normalized_term,
            "normalized_match": matched_normalized
        }
    
    def find_top_matches(
        self, 
        term: str, 
        limit: int = 5,
        min_score: int = 50
    ) -> List[Dict[str, Any]]:
        if not self.known_exams:
            return []
        
        normalized_term = self._normalize(term)
        matches_normalized = get_close_matches(normalized_term, self._normalized_exams.keys(), n=limit, cutoff=min_score/100.0)
        
        results = []
        for matched_normalized in matches_normalized:
            score = int(SequenceMatcher(None, normalized_term, matched_normalized).ratio() * 100)
            matched_exam = self._normalized_exams[matched_normalized]
            
            if score >= 85:
                confidence = "high"
            elif score >= 70:
                confidence = "medium"
            else:
                confidence = "low"
            
            results.append({
                "term": term,
                "match": matched_exam,
                "score": score,
                "confidence": confidence
            })
        
        return results
    
    def batch_match(
        self, 
        terms: List[str],
        auto_accept_threshold: int = 85,
        suggest_threshold: int = 70
    ) -> Dict[str, List[Dict]]:
        result = {
            "auto_accepted": [],
            "suggestions": [],
            "uncertain": [],
            "not_found": []
        }
        
        for term in terms:
            match = self.find_best_match(term, min_score=50)
            
            if not match:
                result["not_found"].append({"term": term})
                continue
            
            if match["score"] >= auto_accept_threshold:
                result["auto_accepted"].append(match)
            elif match["score"] >= suggest_threshold:
                alternatives = self.find_top_matches(term, limit=3, min_score=suggest_threshold)
                match["alternatives"] = alternatives[1:] if len(alternatives) > 1 else []
                result["suggestions"].append(match)
            else:
                alternatives = self.find_top_matches(term, limit=3, min_score=50)
                match["alternatives"] = alternatives
                result["uncertain"].append(match)
        
        return result

    def calculate_real_confidence(self, ocr_confidence: float, fuzzy_score: int) -> float:
        fuzzy_conf = fuzzy_score / 100.0
        real_confidence = (ocr_confidence * 0.3) + (fuzzy_conf * 0.7)
        return real_confidence

# Singleton (será inicializado com exames do BigQuery)
fuzzy_matcher = FuzzyMatcher()
