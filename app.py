"""
Entry point for Render deployment
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

# Import the FastAPI app
from backend.main import app

# This is what Render/Gunicorn will use
application = app
