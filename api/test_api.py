import requests

url = "http://localhost:8000/api/ocr"
files = {'file': ('test_payload.pdf', open('test_payload.pdf', 'rb'), 'application/pdf')}

try:
    print(f"Sending request to {url}...")
    r = requests.post(url, files=files)
    print(f"Status Code: {r.status_code}")
    print(f"Response: {r.text[:500]}...")
except Exception as e:
    print(f"Error: {e}")
