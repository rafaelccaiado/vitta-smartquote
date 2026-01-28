from rapidfuzz import fuzz, process
from typing import List, Dict, Tuple, Optional

class FuzzyMatcher:
    """
    Matching inteligente de termos usando algoritmos de similaridade.
    Mais robusto que busca exata para lidar com erros de OCR.
    """
    
    def __init__(self, known_exams: List[str] = None):
        """
        Args:
            known_exams: Lista de exames conhecidos (do BigQuery)
        """
        self.known_exams = known_exams or []
        self._normalized_exams = {}
        
        # Criar mapa normalizado
        if self.known_exams:
            self._build_normalized_map()
    
    def _build_normalized_map(self):
        """Cria mapa de exames normalizados para busca rápida"""
        for exam in self.known_exams:
            normalized = self._normalize(exam)
            self._normalized_exams[normalized] = exam
    
    def _normalize(self, text: str) -> str:
        """Normaliza texto para comparação"""
        import unicodedata
        # Remove acentos
        text = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('ASCII')
        # Lowercase e remove espaços extras
        return text.lower().strip()
    
    def update_known_exams(self, exams: List[str]):
        """Atualiza lista de exames conhecidos"""
        self.known_exams = exams
        self._build_normalized_map()
    
    def find_best_match(
        self, 
        term: str, 
        min_score: int = 50
    ) -> Optional[Dict[str, any]]:
        """
        Encontra melhor match para um termo.
        
        Args:
            term: Termo a buscar
            min_score: Score mínimo para considerar match (0-100)
            
        Returns:
            {
                "term": termo original,
                "match": exame matched,
                "score": score de similaridade (0-100),
                "confidence": "high" | "medium" | "low"
            }
            ou None se nenhum match acima do threshold
        """
        if not self.known_exams:
            return None
        
        # Normalizar termo
        normalized_term = self._normalize(term)
        
        # Buscar melhor match usando Jaro-Winkler (melhor para nomes)
        result = process.extractOne(
            normalized_term,
            self._normalized_exams.keys(),
            scorer=fuzz.ratio,  # Levenshtein ratio
            score_cutoff=min_score
        )
        
        if not result:
            return None
        
        matched_normalized, score, _ = result
        matched_exam = self._normalized_exams[matched_normalized]
        
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
    ) -> List[Dict[str, any]]:
        """
        Encontra top N matches para um termo.
        Útil para sugestões ao usuário.
        
        Args:
            term: Termo a buscar
            limit: Número máximo de resultados
            min_score: Score mínimo
            
        Returns:
            Lista de matches ordenados por score
        """
        if not self.known_exams:
            return []
        
        normalized_term = self._normalize(term)
        
        # Buscar top matches
        results = process.extract(
            normalized_term,
            self._normalized_exams.keys(),
            scorer=fuzz.ratio,
            limit=limit,
            score_cutoff=min_score
        )
        
        matches = []
        for matched_normalized, score, _ in results:
            matched_exam = self._normalized_exams[matched_normalized]
            
            if score >= 85:
                confidence = "high"
            elif score >= 70:
                confidence = "medium"
            else:
                confidence = "low"
            
            matches.append({
                "term": term,
                "match": matched_exam,
                "score": score,
                "confidence": confidence
            })
        
        return matches
    
    def batch_match(
        self, 
        terms: List[str],
        auto_accept_threshold: int = 85,
        suggest_threshold: int = 70
    ) -> Dict[str, List[Dict]]:
        """
        Processa lista de termos e classifica por confiança.
        
        Args:
            terms: Lista de termos
            auto_accept_threshold: Score para auto-aceitar (>=85)
            suggest_threshold: Score para sugerir ao usuário (>=70)
            
        Returns:
            {
                "auto_accepted": [...],  # Score >= 85
                "suggestions": [...],     # 70 <= Score < 85
                "uncertain": [...],       # Score < 70
                "not_found": [...]        # Sem match
            }
        """
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
                # Buscar alternativas para sugestão
                alternatives = self.find_top_matches(term, limit=3, min_score=suggest_threshold)
                match["alternatives"] = alternatives[1:] if len(alternatives) > 1 else []
                result["suggestions"].append(match)
            else:
                # Baixa confiança - mostrar top 3 opções
                alternatives = self.find_top_matches(term, limit=3, min_score=50)
                match["alternatives"] = alternatives
                result["uncertain"].append(match)
        
        return result
    
    def calculate_real_confidence(self, ocr_confidence: float, fuzzy_score: int) -> float:
        """
        Calcula confiança real combinando OCR e fuzzy matching.
        
        Args:
            ocr_confidence: Confiança do Google Vision (0.0-1.0)
            fuzzy_score: Score do fuzzy match (0-100)
            
        Returns:
            Confiança real (0.0-1.0)
        """
        # Converter fuzzy score para 0-1
        fuzzy_conf = fuzzy_score / 100.0
        
        # Média ponderada (fuzzy tem mais peso pois valida contra catálogo)
        real_confidence = (ocr_confidence * 0.3) + (fuzzy_conf * 0.7)
        
        return real_confidence

# Singleton (será inicializado com exames do BigQuery)
fuzzy_matcher = FuzzyMatcher()
