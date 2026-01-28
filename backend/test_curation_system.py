"""
Script de teste para demonstrar o sistema de curadoria
"""
from validation_logic import ValidationService
from bigquery_client import BigQueryClient
from services.missing_terms_logger import missing_terms_logger

# Simular uso real com termos problemáticos
test_cases = [
    ("Plano Piloto", [
        "Hemograma completo",  # Deve funcionar (exact/synonym)
        "Perfil lipídico",      # Deve funcionar (synonym -> lipidograma)
        "H.pylori",             # Deve funcionar (synonym)
        "Coprologico funcional", # NÃO EXISTE - vai logar
        "Exame inexistente XYZ", # NÃO EXISTE - vai logar
        "Glicemia jejum",        # Fuzzy match - vai sugerir sinônimo
    ])
]

print("🧪 Testando sistema de curadoria...\n")

bq_client = BigQueryClient()

for unit, terms in test_cases:
    print(f"📍 Unidade: {unit}")
    print(f"📝 Termos: {len(terms)}\n")
    
    results = ValidationService.validate_batch(terms, unit, bq_client)
    
    print(f"✅ Confirmados: {results['stats']['confirmed']}")
    print(f"⚠️  Pendentes: {results['stats']['pending']}")
    print(f"❌ Não encontrados: {results['stats']['not_found']}\n")

# Gerar relatório
print("=" * 60)
print("📊 RELATÓRIO DE CURADORIA")
print("=" * 60)
print()

report = missing_terms_logger.generate_report()
print(report)

# Exportar para arquivo
report_file = missing_terms_logger.export_report()
print(f"\n✅ Relatório salvo em: {report_file}")
