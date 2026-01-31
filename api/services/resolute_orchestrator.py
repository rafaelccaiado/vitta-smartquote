from typing import List, Dict, Any

from services.semantic_service import semantic_service
from services.tuss_service import tuss_service
from services.learning_service import learning_service

class ResoluteOrchestrator:
    """
    Vitta Resolute: AI Firewall that standardizes terms BEFORE database search.
    Goal: Eliminate 'Pending' status by resolving medical ambiguity upfront.
    """
    
    @staticmethod
    def standardize_batch(terms: List[str]) -> List[Dict[str, Any]]:
        standardized_items = []
        
        for term in terms:
            resolved_term = ResoluteOrchestrator.resolve_single_term(term)
            standardized_items.append({
                "original": term,
                "resolved": resolved_term["term"],
                "source": resolved_term["source"],
                "confidence": resolved_term["confidence"]
            })
            
        return standardized_items

    @staticmethod
    def resolve_single_term(term: str) -> Dict[str, Any]:
        term_clean = term.strip().lower()
        
        # 1. Check Learning System (Fastest)
        learned = learning_service.get_learned_match(term_clean)
        if learned:
            return {"term": learned, "source": "learning", "confidence": 1.0}
            
        # 2. Check TUSS/LOINC Bridge
        # Note: TussService might return None or a synonym
        tuss_match = tuss_service.search(term_clean)
        if tuss_match:
            return {"term": tuss_match, "source": "tuss_bridge", "confidence": 1.0}
            
        # 3. AI Semantic Normalization (Smartest)
        # Use Gemini to find the most probable medical name
        try:
            ai_resolved = semantic_service.normalize_term(term_clean)
            if ai_resolved and ai_resolved != term_clean:
                # Basic confidence check (if it changed significantly it might be good)
                return {"term": ai_resolved, "source": "semantic_ai", "confidence": 0.8}
        except Exception as e:
            print(f"❌ Resolute AI Error for '{term}': {e}")

        return {"term": term_clean, "source": "original", "confidence": 0.0}

resolute_orchestrator = ResoluteOrchestrator()
