import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'Health_Chatbot-main')))

from backend.database.chromadb_manager import ChromaDBManager
from backend.config import Config

try:
    config = Config()
    db = ChromaDBManager(config.CHROMA_DB_PATH)
    
    print(f"Checking chats for 'local_user' in {config.CHROMA_DB_PATH}")
    chats = db.get_recent_chats("local_user")
    print(f"Found {len(chats)} chats:")
    for chat in chats:
        print(f"- {chat.get('user_message')} -> {chat.get('bot_message')}")

except Exception as e:
    print(f"Error: {e}")
