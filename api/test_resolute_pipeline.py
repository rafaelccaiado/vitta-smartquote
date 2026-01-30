import sys
import os

# Set up paths so we can import from 'api' as a root for 'services'
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API_DIR = os.path.join(PROJECT_ROOT, "api")
if API_DIR not in sys.path:
    sys.path.append(API_DIR)

# Mock modules
class MockLearning:
    def get_learned_match(self, term): return None

class MockLogger:
    def log_fuzzy_match(self, **kwargs): pass
    def log_not_found(self, **kwargs): pass

class MockPDCA:
    def log_fca(self, **kwargs): pass

class MockSemantic:
    def normalize_batch(self, terms): return {}
    def normalize_term(self, term): 
        if "GLICADA" in term.upper(): return "HEMOGLOBINA GLICADA (A1C)"
        return term

# Create mock objects
mock_learning = MockLearning()
mock_logger = MockLogger()
mock_pdca = MockPDCA()
mock_semantic = MockSemantic()

# Mock dependencies in sys.modules
sys.modules["services"] = type("module", (), {})
sys.modules["services.learning_service"] = type("module", (), {"learning_service": mock_learning})
sys.modules["services.missing_terms_logger"] = type("module", (), {"missing_terms_logger": mock_logger})
sys.modules["services.pdca_service"] = type("module", (), {"pdca_service": mock_pdca})
sys.modules["services.semantic_service"] = type("module", (), {"semantic_service": mock_semantic})

# Now import the real orchestrator and service
from services.resolute_orchestrator import resolute_orchestrator
from validation_logic import ValidationService

# Mocking BigQuery Client
class MockBQClient:
    def get_all_exams(self, unit):
        return [
            {"item_id": 1, "item_name": "HEMOGLOBINA GLICADA (A1C)", "search_name": "hemoglobina glicada (a1c)", "price": 45.0},
            {"item_id": 2, "item_name": "TGO (AST) TRANSAMINASE OXALACETICA", "search_name": "tgo (ast) transaminase oxalacetica", "price": 24.0},
            {"item_id": 3, "item_name": "25 HIDROXIVITAMINA D (25-OH)", "search_name": "25 hidroxivitamina d (25-oh)", "price": 100.0},
            {"item_id": 4, "item_name": "URINA ROTINA EAS", "search_name": "urina rotina eas", "price": 30.0},
        ]

def test_resolute_pipeline():
    print("🚀 Testing Vitta Resolute AI Pipeline (Zero Pendency Goal)...")
    bq = MockBQClient()
    
    terms = [
        "Glicada", 
        "TGO", 
        "25-OH", 
        "Urina Tipo 1"
    ]
    
    # 1. Test the Orchestrator directly
    print("\n--- Phase 1: Orchestrator Resolution ---")
    standardized = resolute_orchestrator.standardize_batch(terms)
    for res in standardized:
        print(f"Original: {res['original']} -> Resolved: {res['resolved']} ({res['source']})")

    # 2. Test Full Validation Loop
    print("\n--- Phase 2: Full Validation Flow ---")
    result = ValidationService.validate_batch(terms, "Goiânia Centro", bq)
    
    for item in result["items"]:
        print(f"Term: {item['term']} -> Resolved: {item.get('resolved_term', 'N/A')} -> Status: {item['status']}")
        if item['status'] != "confirmed":
             print(f"❌ FAIL: {item['term']} resultou em {item['status']}")
        else:
             print(f"✅ PASS: {item['term']} matched successfully")

    print(f"\nStats: {result['stats']}")

if __name__ == "__main__":
    test_resolute_pipeline()
