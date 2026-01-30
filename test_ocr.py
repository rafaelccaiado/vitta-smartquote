import urllib.request
import urllib.parse
import json
import os
import uuid

def upload_image(url, filepath):
    boundary = uuid.uuid4().hex
    # ... (rest of multipart construction same as before, simplifying for brevity) ...
    with open(filepath, 'rb') as f:
        file_content = f.read()
    filename = os.path.basename(filepath)
    body = []
    body.append(f'--{boundary}'.encode('utf-8'))
    body.append(f'Content-Disposition: form-data; name="file"; filename="{filename}"'.encode('utf-8'))
    body.append('Content-Type: image/png'.encode('utf-8'))
    body.append(''.encode('utf-8'))
    body.append(file_content)
    body.append(f'--{boundary}--'.encode('utf-8'))
    body.append(''.encode('utf-8'))
    body_bytes = b'\r\n'.join(body)
    
    req = urllib.request.Request(url, data=body_bytes)
    req.add_header('Content-Type', f'multipart/form-data; boundary={boundary}')
    req.add_header('User-Agent', 'Python-Urllib-Test')
    
    try:
        with urllib.request.urlopen(req) as response:
            status = response.status
            resp_body = response.read().decode('utf-8')
            print(f"HTTP {status}")
            # Save to file
            with open("ocr_result.json", "w", encoding="utf-8") as f_out:
                f_out.write(resp_body)
            print("Saved to ocr_result.json")
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}")
        print(e.read().decode('utf-8'))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    upload_image("https://vitta-smartquote.vercel.app/api/ocr", "teste.png")
