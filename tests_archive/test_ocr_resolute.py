import sys
import os

# Set up paths
API_DIR = os.path.dirname(os.path.abspath(__file__))
SERVICES_DIR = os.path.join(API_DIR, "services")
if SERVICES_DIR not in sys.path:
    sys.path.append(SERVICES_DIR)

from services.ocr_resolute_auditor import ocr_resolute_auditor

def test_ocr_auditor():
    print("🚀 Testing Vitta Resolute OCR Auditor...")
    
    # Simulation 1: Perfect Extraction
    print("\n--- Scenário 1: Extração Perfeita ---")
    raw_lines = ["HEMOGRAMA", "GLICOSE", "URINA TIPO I"]
    extracted = [
        {"original": "HEMOGRAMA", "corrected": "HEMOGRAMA", "confidence": 1.0},
        {"original": "GLICOSE", "corrected": "GLICOSE", "confidence": 1.0},
        {"original": "URINA TIPO I", "corrected": "URINA TIPO I", "confidence": 1.0}
    ]
    result = ocr_resolute_auditor.audit(raw_lines, extracted)
    print(f"Status: {result['audit_status']} | Accuracy: {result['accuracy_score']} | Coverage: {result['coverage_score']}")
    print(f"Recommendations: {result['recommendations']}")

    # Simulation 2: Missing Exam (Detected by Prefix)
    print("\n--- Scenário 2: Exame Faltante (TSH esquecido) ---")
    raw_lines = ["HEMOGRAMA", "TSH", "DR. JOAO SILVA"]
    extracted = [
        {"original": "HEMOGRAMA", "corrected": "HEMOGRAMA", "confidence": 0.95}
    ]
    result = ocr_resolute_auditor.audit(raw_lines, extracted)
    print(f"Status: {result['audit_status']} | Accuracy: {result['accuracy_score']} | Coverage: {result['coverage_score']}")
    print(f"Missed: {result['missed_candidates']}")
    print(f"Recommendations: {result['recommendations']}")

    # Simulation 3: Noise Leakage (Dr. name leaked as exam)
    print("\n--- Scenário 3: Vazamento de Ruído (Dr. na lista) ---")
    raw_lines = ["HEMOGRAMA", "DR. MARCOS"]
    extracted = [
        {"original": "HEMOGRAMA", "corrected": "HEMOGRAMA", "confidence": 0.95},
        {"original": "DR. MARCOS", "corrected": "DR. MARCOS EXAME", "confidence": 0.4}
    ]
    result = ocr_resolute_auditor.audit(raw_lines, extracted)
    print(f"Status: {result['audit_status']} | Accuracy: {result['accuracy_score']} | Coverage: {result['coverage_score']}")
    print(f"Leaked: {result['noise_leaked']}")
    print(f"Recommendations: {result['recommendations']}")

if __name__ == "__main__":
    test_ocr_auditor()
