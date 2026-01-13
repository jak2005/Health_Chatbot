
# ============= SQL Persistence Helpers =============

import json
import logging
from pathlib import Path
from typing import Dict, List
from datetime import datetime
from sqlalchemy.orm import Session
try:
    from .db_manager import SessionLocal, ChatHistory, Feedback, Appointment, init_db
except ImportError:
    from db_manager import SessionLocal, ChatHistory, Feedback, Appointment, init_db

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

# ============= Appointment Persistence =============

def _save_appointment(appointment_data: Dict) -> int:
    """Save a new appointment to SQLite, returns appointment ID"""
    try:
        db = SessionLocal()
        new_appointment = Appointment(
            user_id=appointment_data.get("user_id", "default_user"),
            user_name=appointment_data.get("user_name", ""),
            user_email=appointment_data.get("user_email", ""),
            user_phone=appointment_data.get("user_phone", ""),
            appointment_type=appointment_data.get("appointment_type", "General"),
            preferred_date=appointment_data.get("preferred_date", ""),
            preferred_time=appointment_data.get("preferred_time", ""),
            notes=appointment_data.get("notes", ""),
            status="pending",
            created_at=datetime.utcnow()
        )
        db.add(new_appointment)
        db.commit()
        appointment_id = new_appointment.id
        db.close()
        return appointment_id
    except Exception as e:
        logger.error(f"Error saving appointment to SQL: {e}")
        return -1

def _get_user_appointments(user_id: str) -> List[Dict]:
    """Get all appointments for a specific user"""
    try:
        db = SessionLocal()
        appointments = db.query(Appointment).filter(
            Appointment.user_id == user_id
        ).order_by(Appointment.created_at.desc()).all()
        db.close()
        
        return [
            {
                "id": a.id,
                "user_name": a.user_name,
                "user_email": a.user_email,
                "user_phone": a.user_phone,
                "appointment_type": a.appointment_type,
                "preferred_date": a.preferred_date,
                "preferred_time": a.preferred_time,
                "notes": a.notes,
                "status": a.status,
                "created_at": a.created_at.isoformat()
            } for a in appointments
        ]
    except Exception as e:
        logger.error(f"Error loading user appointments from SQL: {e}")
        return []

def _get_all_appointments() -> List[Dict]:
    """Get all appointments (admin function)"""
    try:
        db = SessionLocal()
        appointments = db.query(Appointment).order_by(Appointment.created_at.desc()).all()
        db.close()
        
        return [
            {
                "id": a.id,
                "user_id": a.user_id,
                "user_name": a.user_name,
                "user_email": a.user_email,
                "user_phone": a.user_phone,
                "appointment_type": a.appointment_type,
                "preferred_date": a.preferred_date,
                "preferred_time": a.preferred_time,
                "notes": a.notes,
                "status": a.status,
                "created_at": a.created_at.isoformat()
            } for a in appointments
        ]
    except Exception as e:
        logger.error(f"Error loading all appointments from SQL: {e}")
        return []

def _update_appointment_status(appointment_id: int, new_status: str) -> bool:
    """Update the status of an appointment"""
    try:
        db = SessionLocal()
        appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
        if appointment:
            appointment.status = new_status
            db.commit()
            db.close()
            return True
        db.close()
        return False
    except Exception as e:
        logger.error(f"Error updating appointment status: {e}")
        return False

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
