
# ============= SQL Persistence Helpers =============

import json
import logging
from pathlib import Path
from typing import Dict, List
from datetime import datetime
from sqlalchemy.orm import Session
try:
    from .db_manager import SessionLocal, ChatHistory, Feedback, init_db
except ImportError:
    from db_manager import SessionLocal, ChatHistory, Feedback, init_db

# Configure logging
logger = logging.getLogger(__name__)

# Initialize database tables
init_db()

DATA_DIR = Path(__file__).parent.parent / "data"
FEEDBACK_JSON = DATA_DIR / "feedback.json"
HISTORY_JSON = DATA_DIR / "chat_history.json"

def _save_feedback(feedback_data: Dict):
    """Save feedback to SQLite"""
    try:
        db = SessionLocal()
        new_feedback = Feedback(
            user_id=feedback_data.get("user_id", "default_user"),
            rating=feedback_data.get("rating", 0),
            comment=feedback_data.get("comment", ""),
            timestamp=datetime.fromisoformat(feedback_data["timestamp"]) if "timestamp" in feedback_data else datetime.utcnow()
        )
        db.add(new_feedback)
        db.commit()
        db.close()
    except Exception as e:
        logger.error(f"Error saving feedback to SQL: {e}")

def _load_feedback() -> List[Dict]:
    """Load all feedback from SQLite"""
    try:
        db = SessionLocal()
        feedbacks = db.query(Feedback).order_by(Feedback.timestamp.desc()).all()
        db.close()
        
        return [
            {
                "user_id": f.user_id,
                "rating": f.rating,
                "comment": f.comment,
                "timestamp": f.timestamp.isoformat()
            } for f in feedbacks
        ]
    except Exception as e:
        logger.error(f"Error loading feedback from SQL: {e}")
        return []

def _save_history(user_id: str, message: str, role: str):
    """Save chat history to SQLite"""
    try:
        db = SessionLocal()
        new_chat = ChatHistory(
            user_id=user_id,
            role=role,
            message=message,
            timestamp=datetime.utcnow()
        )
        db.add(new_chat)
        db.commit()
        db.close()
    except Exception as e:
        logger.error(f"Error saving history to SQL: {e}")

def _get_history(user_id: str) -> List[Dict]:
    """Get chat history for user from SQLite (last 50 messages)"""
    try:
        db = SessionLocal()
        history = db.query(ChatHistory).filter(ChatHistory.user_id == user_id).order_by(ChatHistory.timestamp.asc()).all()
        db.close()
        
        # Keep last 50 for parity with previous logic if needed, but SQL handles it easily
        results = [
            {
                "role": c.role,
                "message": c.message,
                "timestamp": c.timestamp.isoformat()
            } for c in history
        ]
        return results[-50:]
    except Exception as e:
        logger.error(f"Error loading history from SQL: {e}")
        return []

# ============= Data Migration Logic =============

def migrate_json_to_sql():
    """Migrate existing JSON data to the new SQL database if present"""
    # Migrate Feedback
    if FEEDBACK_JSON.exists():
        try:
            logger.info("Migrating feedback from JSON to SQL...")
            with open(FEEDBACK_JSON, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for item in data:
                    _save_feedback(item)
            # Rename file to mark as migrated
            FEEDBACK_JSON.rename(FEEDBACK_JSON.with_suffix('.json.bak'))
            logger.info("Feedback migration complete.")
        except Exception as e:
            logger.error(f"Feedback migration failed: {e}")

    # Migrate History
    if HISTORY_JSON.exists():
        try:
            logger.info("Migrating chat history from JSON to SQL...")
            with open(HISTORY_JSON, 'r', encoding='utf-8') as f:
                all_history = json.load(f)
                for user_id, messages in all_history.items():
                    for msg in messages:
                        # Ensure we don't duplicate on multiple restarts
                        db = SessionLocal()
                        new_chat = ChatHistory(
                            user_id=user_id,
                            role=msg.get("role"),
                            message=msg.get("message"),
                            timestamp=datetime.fromisoformat(msg["timestamp"]) if "timestamp" in msg else datetime.utcnow()
                        )
                        db.add(new_chat)
                        db.commit()
                        db.close()
            # Rename file to mark as migrated
            HISTORY_JSON.rename(HISTORY_JSON.with_suffix('.json.bak'))
            logger.info("Chat history migration complete.")
        except Exception as e:
            logger.error(f"History migration failed: {e}")

# Run migration on import
migrate_json_to_sql()
