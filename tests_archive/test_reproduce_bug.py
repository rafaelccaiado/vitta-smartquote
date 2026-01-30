import sys
import os

# Add the project and api directory to PYTHONPATH
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API_ROOT = os.path.dirname(os.path.abspath(__file__))
if API_ROOT not in sys.path:
    sys.path.append(API_ROOT)
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from typing import List, Dict, Any

# Mocking modules before they are imported by validation_logic
class MockFuzzyMatcher:
    def update_known_exams(self, exams): pass
    def find_best_match(self, term, min_score=0): return {"score": 100, "match": term}
    def find_top_matches(self, term, limit=5, min_score=60): return []

class MockTuss:
    def search(self, term): return None

class MockLogger:
    def log_fuzzy_match(self, **kwargs): pass
    def log_not_found(self, **kwargs): pass

class MockLearning:
    def get_learned_match(self, term): return None

class MockPDCA:
    def log_fca(self, **kwargs): print(f"📊 PDCA Mock Log: {kwargs.get('term')} -> {kwargs.get('strategy')}")

# Inject mocks into sys.modules
sys.modules["services"] = type("module", (), {})
sys.modules["services.fuzzy_matcher"] = type("module", (), {"fuzzy_matcher": MockFuzzyMatcher()})
sys.modules["services.tuss_service"] = type("module", (), {"tuss_service": MockTuss()})
sys.modules["services.missing_terms_logger"] = type("module", (), {"missing_terms_logger": MockLogger()})
sys.modules["services.learning_service"] = type("module", (), {"learning_service": MockLearning()})
sys.modules["services.pdca_service"] = type("module", (), {"pdca_service": MockPDCA()})

from validation_logic import ValidationService

# Mocking BigQuery Client
class MockBQClient:
    def get_all_exams(self, unit):
        return [
            {"item_id": 1, "item_name": "Hemograma Completo", "search_name": "hemograma completo", "price": 50.0},
            {"item_id": 2, "item_name": "Glicose", "search_name": "glicose", "price": 20.0},
            {"item_id": 3, "item_name": "Hemoglobina", "search_name": "hemoglobina", "price": 15.0},
            {"item_id": 4, "item_name": "Hemoglobina Glicada (A1C)", "search_name": "hemoglobina glicada", "price": 45.0},
            {"item_id": 5, "item_name": "Urina Rotina EAS", "search_name": "urina rotina eas", "price": 30.0},
            {"item_id": 6, "item_name": "Vitamina B12", "search_name": "vitamina b12", "price": 60.0},
            # Catalogs often have messy names with punctuation
            {"item_id": 7, "item_name": "25-HIDROXIVITAMINA D", "search_name": "25-hidroxivitamina d", "price": 100.0},
            {"item_id": 8, "item_name": "TGO - TRANSAMINASE OXALACETICA", "search_name": "tgo - transaminase oxalacetica", "price": 24.0},
            {"item_id": 9, "item_name": "TGP - TRANSAMINASE PIRUVICA", "search_name": "tgp - transaminase piruvica", "price": 24.0},
            {"item_id": 10, "item_name": "VHS - HEMOSSEDIMENTACAO EXAMES LABORATORIAIS", "search_name": "vhs - hemossedimentacao exames laboratoriais", "price": 49.0},
        ]

def test_validation():
    print("Testing Validation Heuristics (Lab Specialist Phase - V84 Punctuation Test)...")
    bq = MockBQClient()
    terms = [
        "Hemograma", 
        "Glicose", 
        "Hemoglobina Glicada", 
        "Urina Tipo 1", 
        "Vit B12",
        "Vitamina D (25-OH)", # Punctuation variation
        "TGO (AST)",          # Partial match + Parênteses
        "TGP (ALT)",          # Partial match + Parênteses
        "VHS"                 # Direct match
    ]
    
    result = ValidationService.validate_batch(terms, "Goiânia Centro", bq)
    
    for item in result["items"]:
        term = item["term"]
        status = item["status"]
        matches = item["matches"]
        best_match = matches[0]["item_name"] if matches else "NONE"
        strategy = item.get("match_strategy", "N/A")
        
        print(f"Term: {term} -> Status: {status} -> Best Match: {best_match} ({strategy})")
        
        # Specific assertions
        if term == "Hemoglobina Glicada":
            if "Glicada" not in best_match:
                print("❌ FAIL: Hemoglobina Glicada matched generic Hemoglobina")
            else:
                print("✅ PASS: Hemoglobina Glicada matched correctly")
        
        if "TGO" in term:
            if "TGO" in best_match:
                print("✅ PASS: TGO matched via synonym + substring")
            else:
                print("❌ FAIL: TGO failed to match")

    print(f"Stats: {result['stats']}")

if __name__ == "__main__":
    test_validation()
