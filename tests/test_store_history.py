import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'Health_Chatbot-main')))

from backend.database.chromadb_manager import ChromaDBManager
from backend.config import Config

try:
    config = Config()
    db = ChromaDBManager(config.CHROMA_DB_PATH)
    
    print("Simulating chat storage for 'local_user'...")
    success = db.store_chat("local_user", "Hello debug", "Hi there debug")
    print(f"Store result: {success}")
    
    print("Checking if it's there...")
    chats = db.get_recent_chats("local_user")
    print(f"Found {len(chats)} chats.")

except Exception as e:
    print(f"Error: {e}")
