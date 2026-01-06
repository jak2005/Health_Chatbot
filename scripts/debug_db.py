import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'Health_Chatbot-main')))

from backend.database.chromadb_manager import ChromaDBManager
from backend.config import Config

config = Config()
db = ChromaDBManager(config.CHROMA_DB_PATH)

print("Checking history for 'local_user'...")
history = db.get_recent_chats("local_user")
print(f"Found {len(history)} chats.")
for chat in history:
    print(f"- {chat.get('user_message')} (Timestamp: {chat.get('timestamp')})")

print("\nChecking all chats (first 10)...")
try:
    all_chats = db.chat_history.get(limit=10)
    if all_chats and all_chats['ids']:
        for i, meta in enumerate(all_chats['metadatas']):
            print(f"ID: {all_chats['ids'][i]}, User: {meta.get('user_id')}")
except Exception as e:
    print(f"Error listing all: {e}")
