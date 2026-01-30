import unittest
from unittest.mock import MagicMock, patch
from ocr_processor import OCRProcessor

class TestOCRPipelineLogic(unittest.TestCase):
    def setUp(self):
        # Patch the client initialization to avoid actual API calls
        with patch('google.cloud.vision.ImageAnnotatorClient'):
            self.processor = OCRProcessor()
            self.processor.client = MagicMock()
            self.processor.use_llm_correction = False # Disable LLM for basic logic test

    def test_apply_deterministic_rules(self):
        self.assertEqual(self.processor._apply_deterministic_rules("4 754"), "TSH")
        self.assertEqual(self.processor._apply_deterministic_rules("T4 Liore"), "T4 Livre")
        self.assertEqual(self.processor._apply_deterministic_rules("Hemogroma"), "Hemograma")
        self.assertEqual(self.processor._apply_deterministic_rules("Urreia"), "Ureia")

    def test_smart_parse(self):
        raw_text = """
        CLINICA VITTA
        CNPJ: 00.000.000/0001-00
        Paciente: João Silva
        Data: 28/01/2026
        Solicito:
        - Hemograma
        - TSH
        * Glicemia
        Ass: Dr. Médico
        """
        parsed = self.processor._smart_parse(raw_text)
        self.assertIn("Hemograma", parsed)
        self.assertIn("TSH", parsed)
        self.assertIn("Glicemia", parsed)
        self.assertNotIn("CLINICA VITTA", parsed)
        self.assertNotIn("CNPJ", parsed)
        self.assertNotIn("Paciente", parsed)

    def test_apply_context_rules(self):
        terms = ["TSH", "COLESTEROL TOTAL", "GLICEMIA"]
        result_terms, stats = self.processor._apply_context_rules(terms)
        self.assertEqual(result_terms, terms)
        self.assertIn("corrections", stats)

    @patch('ocr_processor.vision.Image')
    def test_process_image_flow(self, mock_vision_image):
        # Mocking Google Vision Response
        mock_response = MagicMock()
        mock_response.error.message = ""
        mock_response.full_text_annotation.text = "Solicito:\n4 754\nGlicemia"
        self.processor.client.document_text_detection.return_value = mock_response
        
        result = self.processor.process_image(b"fake_image_bytes")
        print(f"DEBUG process_image text: {repr(result['text'])}")
        
        self.assertIn("TSH", result["text"])
        self.assertIn("Glicemia", result["text"])
        self.assertEqual(result["stats"]["auto_confirmed"], 1)

if __name__ == "__main__":
    import sys
    suite = unittest.TestLoader().loadTestsFromTestCase(TestOCRPipelineLogic)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not result.wasSuccessful():
        print("\n--- FAILURES ---")
        for failure in result.failures:
            print(f"FAILURE IN {failure[0]}:\n{failure[1]}")
        for error in result.errors:
            print(f"ERROR IN {error[0]}:\n{error[1]}")
        sys.exit(1)
