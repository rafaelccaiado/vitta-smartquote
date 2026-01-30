from services.semantic_service import semantic_service
import json

test_terms = ["C4", "Ac. Anti-TPO", "Vit D", "Glicemia", "Hemagroma", "TSH Ultra"]
print(f"🧪 Testing Semantic Service with: {test_terms}")

try:
    result = semantic_service.normalize_batch(test_terms)
    print("\n✅ Result Raw:")
    print(json.dumps(result, indent=2, ensure_ascii=False))
except Exception as e:
    print(f"\n❌ Error: {e}")
