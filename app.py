"""
Entry point for Render deployment
"""
import sys
import os

# Add backend folder to Python path
backend_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend')
sys.path.insert(0, backend_path)

# Import the FastAPI app from main.py
from main import app

# Export for uvicorn
application = app
