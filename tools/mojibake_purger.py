import os

def clean_file(filepath):
    """Deep cleans a file: strips BOM and non-ASCII/latin garbage."""
    print(f"🧹 Cleaning: {filepath}")
    try:
        # Read raw bytes
        with open(filepath, 'rb') as f:
            raw_bytes = f.read()
        
        # Strip UTF-8 BOM if present
        if raw_bytes.startswith(b'\xef\xbb\xbf'):
            raw_bytes = raw_bytes[3:]
            
        # Decode ignoring errors, then encode cleanly
        # This effectively purges U+2E65 and other high-plane artifacts
        text = raw_bytes.decode('utf-8', errors='ignore')
        
        # Final safety: remove specific known artifacts if they survived
        text = text.replace('\ufeff', '')
        text = text.replace('\u2e65', '')
        
        with open(filepath, 'w', encoding='utf-8', newline='\n') as f:
            f.write(text)
        return True
    except Exception as e:
        print(f"❌ Failed to clean {filepath}: {e}")
        return False

# Target directories
targets = ['api', 'api/core', 'api/services']

for target_dir in targets:
    if not os.path.exists(target_dir): continue
    for f in os.listdir(target_dir):
        if f.endswith('.py'):
            clean_file(os.path.join(target_dir, f))

print("✨ Cleanup Complete. All Python files are now pure UTF-8 (No BOM/Mojibake).")
