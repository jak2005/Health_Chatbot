
# ============= SQL Persistence Helpers =============

import json
import logging
from pathlib import Path
from typing import Dict, List
from datetime import datetime
from sqlalchemy.orm import Session
try:
    from .db_manager import SessionLocal, ChatHistory, Feedback, Appointment, SecurityLog, Message, User, init_db
    from .security import encrypt, decrypt, sanitize, validate_email, validate_phone, log_event
except ImportError:
    from db_manager import SessionLocal, ChatHistory, Feedback, Appointment, SecurityLog, Message, User, init_db
    from security import encrypt, decrypt, sanitize, validate_email, validate_phone, log_event

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
    """Save a new appointment to SQLite with encrypted sensitive data, returns appointment ID"""
    try:
        # Validate inputs
        email = appointment_data.get("user_email", "")
        phone = appointment_data.get("user_phone", "")
        
        email_valid, email_err = validate_email(email)
        if not email_valid:
            logger.warning(f"Invalid email format: {email_err}")
        
        phone_valid, phone_err = validate_phone(phone)
        if not phone_valid:
            logger.warning(f"Invalid phone format: {phone_err}")
        
        # Sanitize text inputs
        user_name = sanitize(appointment_data.get("user_name", ""), max_length=100)
        notes = sanitize(appointment_data.get("notes", ""), max_length=1000)
        
        # Encrypt sensitive data
        encrypted_email = encrypt(email)
        encrypted_phone = encrypt(phone)
        encrypted_notes = encrypt(notes) if notes else ""
        
        db = SessionLocal()
        new_appointment = Appointment(
            user_id=appointment_data.get("user_id", "default_user"),
            doctor_id=appointment_data.get("doctor_id"),
            doctor_name=appointment_data.get("doctor_name"),
            department=appointment_data.get("department"),
            user_name=user_name,
            user_email=encrypted_email,
            user_phone=encrypted_phone,
            appointment_type=appointment_data.get("appointment_type", "General"),
            preferred_date=appointment_data.get("preferred_date", ""),
            preferred_time=appointment_data.get("preferred_time", ""),
            notes=encrypted_notes,
            status="pending",
            created_at=datetime.utcnow(),
            is_encrypted=1
        )
        db.add(new_appointment)
        db.commit()
        appointment_id = new_appointment.id
        
        # Log the data access event
        log_event("APPOINTMENT_CREATED", appointment_data.get("user_id"), f"Appointment ID: {appointment_id}")
        
        db.close()
        return appointment_id
    except Exception as e:
        logger.error(f"Error saving appointment to SQL: {e}")
        return -1

def _get_user_appointments(user_id: str) -> List[Dict]:
    """Get all appointments for a specific user, decrypting sensitive data"""
    try:
        db = SessionLocal()
        appointments = db.query(Appointment).filter(
            Appointment.user_id == user_id
        ).order_by(Appointment.created_at.desc()).all()
        db.close()
        
        # Log data access
        log_event("DATA_ACCESS", user_id, f"Accessed {len(appointments)} appointments")
        
        result = []
        for a in appointments:
            # Decrypt sensitive fields if encrypted
            is_encrypted = getattr(a, 'is_encrypted', 0)
            
            if is_encrypted:
                user_email = decrypt(a.user_email) if a.user_email else ""
                user_phone = decrypt(a.user_phone) if a.user_phone else ""
                notes = decrypt(a.notes) if a.notes else ""
            else:
                user_email = a.user_email
                user_phone = a.user_phone
                notes = a.notes
            
            result.append({
                "id": a.id,
                "user_name": a.user_name,
                "user_email": user_email,
                "user_phone": user_phone,
                "appointment_type": a.appointment_type,
                "preferred_date": a.preferred_date,
                "preferred_time": a.preferred_time,
                "notes": notes,
                "status": a.status,
                "created_at": a.created_at.isoformat()
            })
        
        return result
    except Exception as e:
        logger.error(f"Error loading user appointments from SQL: {e}")
        return []

def _get_all_appointments() -> List[Dict]:
    """Get all appointments (admin function) with decrypted sensitive data"""
    try:
        db = SessionLocal()
        appointments = db.query(Appointment).order_by(Appointment.created_at.desc()).all()
        db.close()
        
        # Log admin data access
        log_event("ADMIN_DATA_ACCESS", "admin", f"Accessed all appointments ({len(appointments)} records)")
        
        result = []
        for a in appointments:
            # Decrypt sensitive fields if encrypted
            is_encrypted = getattr(a, 'is_encrypted', 0)
            
            if is_encrypted:
                user_email = decrypt(a.user_email) if a.user_email else ""
                user_phone = decrypt(a.user_phone) if a.user_phone else ""
                notes = decrypt(a.notes) if a.notes else ""
            else:
                user_email = a.user_email
                user_phone = a.user_phone
                notes = a.notes
            
            result.append({
                "id": a.id,
                "user_id": a.user_id,
                "user_name": a.user_name,
                "user_email": user_email,
                "user_phone": user_phone,
                "appointment_type": a.appointment_type,
                "preferred_date": a.preferred_date,
                "preferred_time": a.preferred_time,
                "notes": notes,
                "status": a.status,
                "created_at": a.created_at.isoformat()
            })
        
        return result
    except Exception as e:
        logger.error(f"Error loading all appointments from SQL: {e}")
        return []

def _update_appointment_status(appointment_id: int, new_status: str) -> bool:
    """Update the status of an appointment with audit logging"""
    try:
        db = SessionLocal()
        appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
        if appointment:
            old_status = appointment.status
            appointment.status = new_status
            db.commit()
            
            # Log status change
            log_event("APPOINTMENT_STATUS_CHANGE", appointment.user_id, 
                     f"Appointment {appointment_id}: {old_status} -> {new_status}")
            
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


# ============= Message Functions =============

def _send_message(sender_id: int, receiver_id: int, sender_name: str, content: str) -> int:
    """Send a message from one user to another"""
    try:
        db = SessionLocal()
        new_msg = Message(
            sender_id=sender_id,
            receiver_id=receiver_id,
            sender_name=sender_name,
            content=encrypt(content),  # Encrypt message content
            timestamp=datetime.utcnow(),
            read=0
        )
        db.add(new_msg)
        db.commit()
        msg_id = new_msg.id
        db.close()
        log_event("MESSAGE_SENT", str(sender_id), f"To user {receiver_id}")
        return msg_id
    except Exception as e:
        logger.error(f"Error sending message: {e}")
        return -1

def _get_conversation(user1_id: int, user2_id: int) -> List[Dict]:
    """Get conversation between two users"""
    try:
        db = SessionLocal()
        messages = db.query(Message).filter(
            ((Message.sender_id == user1_id) & (Message.receiver_id == user2_id)) |
            ((Message.sender_id == user2_id) & (Message.receiver_id == user1_id))
        ).order_by(Message.timestamp.asc()).all()
        db.close()
        
        return [
            {
                "id": m.id,
                "sender_id": m.sender_id,
                "receiver_id": m.receiver_id,
                "sender_name": m.sender_name,
                "content": decrypt(m.content) if m.content else "",
                "timestamp": m.timestamp.isoformat(),
                "read": bool(m.read)
            } for m in messages
        ]
    except Exception as e:
        logger.error(f"Error getting conversation: {e}")
        return []

def _get_user_conversations(user_id: int) -> List[Dict]:
    """Get all conversations for a user (unique chat partners)"""
    try:
        db = SessionLocal()
        # Get all messages involving this user
        messages = db.query(Message).filter(
            (Message.sender_id == user_id) | (Message.receiver_id == user_id)
        ).order_by(Message.timestamp.desc()).all()
        db.close()
        
        # Extract unique conversation partners
        conversations = {}
        for m in messages:
            partner_id = m.receiver_id if m.sender_id == user_id else m.sender_id
            if partner_id not in conversations:
                conversations[partner_id] = {
                    "partner_id": partner_id,
                    "partner_name": m.sender_name if m.sender_id == partner_id else "You",
                    "last_message": decrypt(m.content)[:50] if m.content else "",
                    "last_timestamp": m.timestamp.isoformat(),
                    "unread": 0
                }
            # Count unread messages from this partner
            if m.sender_id == partner_id and not m.read:
                conversations[partner_id]["unread"] += 1
        
        return list(conversations.values())
    except Exception as e:
        logger.error(f"Error getting conversations: {e}")
        return []

def _mark_messages_read(reader_id: int, sender_id: int):
    """Mark all messages from sender to reader as read"""
    try:
        db = SessionLocal()
        db.query(Message).filter(
            (Message.sender_id == sender_id) & (Message.receiver_id == reader_id)
        ).update({Message.read: 1})
        db.commit()
        db.close()
    except Exception as e:
        logger.error(f"Error marking messages read: {e}")


# ============= Doctor-Specific Functions =============

def _get_doctor_appointments(doctor_id: int) -> List[Dict]:
    """Get all appointments for a specific doctor"""
    try:
        db = SessionLocal()
        appointments = db.query(Appointment).filter(
            Appointment.doctor_id == doctor_id
        ).order_by(Appointment.created_at.desc()).all()
        
        result = []
        for a in appointments:
            # Look up numerical patient ID by username
            patient = db.query(User).filter(User.username == a.user_id).first()
            patient_id = patient.id if patient else None
            
            result.append({
                "id": a.id,
                "user_id": a.user_id,
                "patient_id": patient_id,  # Numerical ID for messaging
                "user_name": a.user_name,
                "user_email": decrypt(a.user_email) if a.is_encrypted and a.user_email else a.user_email,
                "user_phone": decrypt(a.user_phone) if a.is_encrypted and a.user_phone else a.user_phone,
                "department": a.department,
                "appointment_type": a.appointment_type,
                "preferred_date": a.preferred_date,
                "preferred_time": a.preferred_time,
                "notes": decrypt(a.notes) if a.is_encrypted and a.notes else a.notes,
                "status": a.status,
                "created_at": a.created_at.isoformat()
            })
        db.close()
        return result
    except Exception as e:
        logger.error(f"Error getting doctor appointments: {e}")
        return []

def _get_doctor_patients(doctor_id: int) -> List[Dict]:
    """Get all patients who have accepted appointments with this doctor"""
    try:
        db = SessionLocal()
        # Get unique patients with accepted appointments
        appointments = db.query(Appointment).filter(
            (Appointment.doctor_id == doctor_id) & 
            (Appointment.status == "accepted")
        ).all()
        
        # Extract unique patients
        patients = {}
        for a in appointments:
            if a.user_id not in patients:
                # Look up numerical patient ID
                patient = db.query(User).filter(User.username == a.user_id).first()
                patient_id = patient.id if patient else None
                
                patients[a.user_id] = {
                    "user_id": a.user_id,
                    "patient_id": patient_id,  # Numerical ID for messaging
                    "user_name": a.user_name,
                    "last_appointment": a.preferred_date,
                    "appointment_count": 0
                }
            patients[a.user_id]["appointment_count"] += 1
        
        db.close()
        return list(patients.values())
    except Exception as e:
        logger.error(f"Error getting doctor patients: {e}")
        return []


# Run migration on import
migrate_json_to_sql()
