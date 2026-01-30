import requests
import json

BASE_URL = "http://localhost:8000"

def test_batch_validation():
    print("\n--- Testing Batch Validation ---")
    payload = {
        "terms": [
            "HEMOGRAMA",          # Deve achar (Confirmed)
            "TSH",                # Deve achar (Confirmed ou Multiple)
            "EXAME_INEXISTENTE",  # Não deve achar (Not Found)
            "HEMOGRAMA",          # Duplicado (Duplicate)
            "GLICOSE"             # Deve achar
        ],
        "unit": "Goiânia Centro"
    }
    
    try:
        r = requests.post(f"{BASE_URL}/api/validate-list", json=payload)
        
        if r.status_code == 200:
            data = r.json()
            print("Status: OK")
            print("Stats:", json.dumps(data.get("stats"), indent=2))
            
            print("\nItems:")
            for item in data.get("items", []):
                print(f"- Term: {item['term']:<20} | Status: {item['status']}")
                
        else:
            print(f"Failed: {r.status_code}")
            print(r.text)
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_batch_validation()
