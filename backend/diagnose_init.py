
import sys
import os
import traceback

# Add parent dir to path if needed (though we are in backend/)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

print("--- DIAGNOSTIC START ---")
try:
    from ocr_processor import OCRProcessor
    print("✅ Import OK")
except Exception as e:
    print(f"❌ Import Failed: {e}")
    traceback.print_exc()
    sys.exit(1)

try:
    print("⏳ Attempting to instantiate OCRProcessor...")
    processor = OCRProcessor()
    print("✅ Instantiation OK")
    
    # Check if loaded dict
    if hasattr(processor, 'exams_dict'):
        print(f"📚 Dictionary keys: {list(processor.exams_dict.keys())}")
        if 'exames' in processor.exams_dict:
             print(f"    - Count: {len(processor.exams_dict['exames'])}")
    
except Exception as e:
    print(f"❌ Instantiation Failed: {e}")
    traceback.print_exc()

print("--- DIAGNOSTIC END ---")
