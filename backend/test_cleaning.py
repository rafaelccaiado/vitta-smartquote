from validation_logic import ValidationService
from typing import List

class MockBQ:
    def search_exams(self, term, unit):
        print(f"  🔎 Buscando no BQ: '{term}'")
        return []

bq = MockBQ()
dirty_terms = [
    "- Hemograma completo", 
    "* Glicose", 
    "14/02/22", 
    "Solicito:", 
    "Dr. Carlos", 
    "Colesterol Total e Frac"
]

print("--- ENTRADA ---")
print(dirty_terms)

print("\n--- PROCESSAMENTO ---")
result = ValidationService.validate_batch(dirty_terms, "Goiânia Centro", bq)

print("\n--- RESULTADO FINAL (ITEMS PROCESSADOS) ---")
for item in result["items"]:
    print(f"Termo Original: '{item['original_term']}' -> Termo Limpo: '{item['term']}'")

cleaned_terms = [i['term'] for i in result['items']]

assert "Hemograma completo" in cleaned_terms, "Falha: Hifen não removido"
assert "Glicose" in cleaned_terms, "Falha: Asterisco não removido"
assert "14/02/22" not in cleaned_terms, "Falha: Data não removida"
assert "Solicito:" not in cleaned_terms, "Falha: Keyword não removida"

print("\n✅ SUCESSO! A limpeza de lógica está funcionando.")
