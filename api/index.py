import os
import sys

# Get the directory of the current file (vitta-smartquote/api)
api_dir = os.path.dirname(os.path.abspath(__file__))
# Root of the project (vitta-smartquote)
root_dir = os.path.dirname(api_dir)
backend_dir = os.path.join(root_dir, 'backend')

# Add root_dir and backend_dir to sys.path
if root_dir not in sys.path:
    sys.path.append(root_dir)
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

# Now import the app
try:
    from backend.main import app
except ImportError as e:
    print(f"Import Error: {e}")
    # Fallback to local import if needed or handle pathing
    raise e
