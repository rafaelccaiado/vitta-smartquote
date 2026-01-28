import requests
import os

BASE_URL = "http://localhost:8000"
IMAGE_PATH = r"C:/Users/rafae/.gemini/antigravity/brain/92778fc1-5d28-41a2-a6ac-d0856d1a1855/pedido_medico_teste_1769524367458.png"

def test_health():
    try:
        r = requests.get(f"{BASE_URL}/")
        print(f"Health Check: {r.status_code} - {r.json()}")
    except Exception as e:
        print(f"Health Check Failed: {e}")

def test_search():
    try:
        payload = {"term": "HEMOGRAMA", "unit": "Goiânia Centro"}
        r = requests.post(f"{BASE_URL}/api/search-exams", json=payload)
        print(f"Search Check: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            print(f"Found {data.get('count')} exams")
            if data.get('exams'):
                print(f"Sample: {data['exams'][0]['item_name']}")
        else:
            print(r.text)
    except Exception as e:
        print(f"Search Check Failed: {e}")

def test_ocr():
    if not os.path.exists(IMAGE_PATH):
        print("Image not found for testing")
        return
        
    try:
        with open(IMAGE_PATH, 'rb') as f:
            files = {'file': ('test.png', f, 'image/png')}
            r = requests.post(f"{BASE_URL}/api/ocr", files=files)
            print(f"OCR Check: {r.status_code}")
            if r.status_code == 200:
                print(f"OCR Result Keys: {r.json().keys()}")
            else:
                print(f"OCR Error: {r.text}")
    except Exception as e:
        print(f"OCR Check Failed: {e}")

if __name__ == "__main__":
    print("--- Starting Integration Tests ---")
    test_health()
    print("\n--- Testing Search ---")
    test_search()
    # print("\n--- Testing OCR (Mocked or Real) ---")
    # test_ocr() # Disable OCR test to save API calls/time if key is missing
    print("\n--- Done ---")
