import urllib.request
import json

payload = {
    "terms": ["Ureia", "Perfil Lipido", "EAS"],
    "unit": "Plano Piloto" 
}

print("Consultando API...")
try:
    req = urllib.request.Request(
        "http://localhost:8000/api/validate-list",
        data=json.dumps(payload).encode('utf-8'),
        headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode('utf-8'))
        print(f"Status: {response.getcode()}")
        print(json.dumps(data, indent=2, ensure_ascii=False))
except Exception as e:
    print(f"Erro: {e}")
