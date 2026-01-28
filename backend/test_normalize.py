import unicodedata

def normalize(text):
    if not text: return ""
    text = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('ASCII')
    return text.lower().strip()

# Teste
terms = [
    "Coprologico funcional",
    "Pesquisa antígeno fecal para H.pylori",
    "coprologico",
    "h.pylori",
    "antigeno fecal"
]

print("Normalização de termos:")
for term in terms:
    print(f"  '{term}' -> '{normalize(term)}'")
