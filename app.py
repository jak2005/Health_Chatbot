"""
Entry point for Render deployment
"""
import sys
import os

# Add backend folder to Python path
backend_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend')
sys.path.insert(0, backend_path)

# Import the FastAPI app from main.py
# Import the FastAPI app from main.py
try:
    from main import app
except Exception as e:
    import traceback
    print("CRITICAL ERROR: Failed to import backend.main")
    traceback.print_exc()
    raise e

# Export for uvicorn
application = app
