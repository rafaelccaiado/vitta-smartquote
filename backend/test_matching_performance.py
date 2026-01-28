from validation_logic import ValidationService
import time

class MockBQ:
    def get_all_exams(self, unit):
        print("  ⏳ [MOCK] Baixando catálogo...")
        # Simula um catálogo real da Vittá
        return [
            {"item_id": 1, "item_name": "HEMOGRAMA COMPLETO", "search_name": "hemograma completo", "price": 10.0},
            {"item_id": 2, "item_name": "URINA TIPO I", "search_name": "urina tipo i", "price": 8.0},
            {"item_id": 3, "item_name": "GLICEMIA", "search_name": "glicemia", "price": 5.0},
            {"item_id": 4, "item_name": "COLESTEROL TOTAL", "search_name": "colesterol total", "price": 7.0},
            {"item_id": 5, "item_name": "TRIGLICERIDES", "search_name": "triglicerides", "price": 7.0},
            {"item_id": 6, "item_name": "TSH", "search_name": "tsh", "price": 15.0},
            {"item_id": 7, "item_name": "T4 LIVRE", "search_name": "t4 livre", "price": 15.0},
            {"item_id": 8, "item_name": "PARASITOLOGICO DE FEZES", "search_name": "parasitologico de fezes", "price": 9.0},
        ]

bq = MockBQ()
inputs = [
    "- Hemograma",         # Limpeza + Fuzzy/Exata no nome curto?
    "EAS",                 # Sinônimo -> Urina Tipo I
    "Glicose",             # Sinônimo -> Glicemia
    "Hemogrimas",          # Typos (Fuzzy) -> Hemograma
    "Colesterol",          # Fuzzy -> Colesterol Total
    "EPF",                 # Sigla -> Parasitológico
    "Ureia"                # Não existe no mock -> Not Found
]

print("--- INICIANDO TESTE DE PERFORMANCE E MATCHING ---")
start = time.time()
result = ValidationService.validate_batch(inputs, "Mock Unit", bq)
end = time.time()

print(f"\n⏱️ Tempo Total: {end - start:.4f}s")
print(f"Items Processados: {len(result['items'])}")

synonym_success = False
fuzzy_success = False

for item in result["items"]:
    clean_term = item['term']
    status = item['status']
    match_name = item['matches'][0]['item_name'] if item['matches'] else "Nenhum"
    strategy = item.get('match_strategy', 'N/A')
    
    print(f"Input: '{item['original_term']}' -> Clean: '{clean_term}' | Status: {status} | Match: {match_name} | Strategy: {strategy}")

    if clean_term == "EAS" and "URINA" in match_name: synonym_success = True
    if clean_term == "Hemogrimas" and "HEMOGRAMA" in match_name: fuzzy_success = True

if synonym_success: print("\n✅ TESTE DE SINÔNIMO (EAS -> URINA): SUCESSO")
else: print("\n❌ FALHA NO SINÔNIMO")

if fuzzy_success: print("✅ TESTE FUZZY (Hemogrimas -> HEMOGRAMA): SUCESSO")
else: print("❌ FALHA NO FUZZY")
