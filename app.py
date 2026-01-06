"""
Root-level FastAPI app entry point for Render deployment.
This file avoids Python module import issues by importing directly.
"""
import os
import sys

# Add project directories to Python path
root_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.join(root_dir, 'backend')

# Ensure both directories are in Python path
for path in [root_dir, backend_dir]:
    if path not in sys.path:
        sys.path.insert(0, path)

# Now import the FastAPI app from backend
from backend.main import app

# For running directly with: python app.py
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)
