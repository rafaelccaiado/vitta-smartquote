import os
import shutil

src_dir = 'api'
dst_dir = 'tests_archive'
patterns = ['test_', 'debug_', 'check_', 'verify_', 'find_', 'list_', 'gen_']
specific = [
    'main.py', 'ocr.py', 'ping.py', 'date.py', 'etl_loinc.py', 
    'compare_speed.py', 'create_loinc_match.py', 'search_funcional.py', 
    'save_debug.py', 'probe_api_debug.py', 'verify_official_client.py', 
    'verify_router.py', 'remote_probe.py'
]

if not os.path.exists(dst_dir):
    os.makedirs(dst_dir)

print(f"🧹 Iniciando limpeza nuclear da pasta {src_dir}...")

moved_count = 0
for f in os.listdir(src_dir):
    f_path = os.path.join(src_dir, f)
    if os.path.isfile(f_path):
        is_unwanted = any(f.startswith(p) for p in patterns) or f in specific
        if is_unwanted and f not in ['index.py', 'qa_proof.py']:
            shutil.move(f_path, os.path.join(dst_dir, f))
            print(f"  -> Movido: {f}")
            moved_count += 1

print(f"✅ Limpeza concluída. {moved_count} arquivos movidos para {dst_dir}.")
