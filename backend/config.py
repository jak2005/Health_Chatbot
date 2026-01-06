# backend/config.py
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

class Config:
    # API Keys
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
    GROQ_API_KEY = os.getenv('GROQ_API_KEY')
    
    
    # Database Configuration
    CHROMA_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'chromadb')
    
    # Model Configuration
    GEMINI_FLASH_MODEL = "gemini-flash-latest"
    
    # Chat Configuration
    MAX_CHAT_HISTORY = 10
    MAX_SUB_QUERIES = 4
    
    # Response Configuration
    DEFAULT_RESPONSE = "I apologize, but I'm having trouble processing your request. Please try again."
    SAFETY_WARNING = "For your safety, please consult a healthcare professional for accurate advice."
    
    # Session Configuration
    STREAMLIT_SESSION_TIMEOUT = 3600  # 1 hour in seconds
