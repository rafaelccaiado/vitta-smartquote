import requests
import time

url = "https://vitta-smartquote.vercel.app/api/health"
print(f"Testing {url}...")

for i in range(5):
    try:
        resp = requests.get(url, timeout=10)
        print(f"Attempt {i+1}: Status {resp.status_code}")
        if resp.status_code == 200:
            print("Payload:", resp.json())
        else:
            print("Error:", resp.text[:200])
    except Exception as e:
        print(f"Attempt {i+1}: Failed - {e}")
    time.sleep(10)
