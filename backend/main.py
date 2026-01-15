"""
HealthLink AI Backend - FastAPI Server with RAG
Supports both Gemini and Groq APIs
Enhanced version with improved error handling, logging, and features
Compatible with Pydantic v1 and ChromaDB v0.3.x
"""

import os
import logging
from pathlib import Path
from typing import List, Optional, Any, Dict
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

# Import persistence helpers
from persistence import _save_feedback, _load_feedback, _save_history, _get_history, _save_appointment, _get_user_appointments, _get_all_appointments, _update_appointment_status

# Import auth helpers
from auth import (
    create_user, authenticate_user, create_access_token,
    decode_token, get_user_by_username, get_user_by_id
)

# Import security helpers
from security import (
    security_manager, sanitize, validate_email, validate_phone,
    validate_username, validate_password, log_event
)

# Pydantic v1 compatible imports
try:
    from pydantic import BaseModel, Field
except ImportError:
    from pydantic.v1 import BaseModel, Field

from rag_service import get_rag_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env.local")
load_dotenv(dotenv_path=Path(__file__).parent / ".env")

# API Keys
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", os.getenv("GOOGLE_API_KEY", ""))
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# Initialize AI client
ai_client = None
ai_provider = None
gemini_model = None

# Try Groq first (more generous free tier), then Gemini
if GROQ_API_KEY:
    try:
        from groq import Groq
        ai_client = Groq(api_key=GROQ_API_KEY)
        ai_provider = "groq"
        logger.info("Using Groq API")
    except Exception as e:
        logger.warning(f"Failed to initialize Groq: {e}")

if not ai_client and GEMINI_API_KEY:
    try:
        # Use google-generativeai (compatible with pydantic v1)
        import google.generativeai as genai
        genai.configure(api_key=GEMINI_API_KEY)
        model_name = os.getenv("MODEL_NAME", "gemini-pro")
        gemini_model = genai.GenerativeModel(model_name)
        ai_client = gemini_model
        ai_provider = "gemini"
        logger.info(f"Using Gemini API with model: {model_name}")
    except Exception as e:
        logger.warning(f"Failed to initialize Gemini: {e}")

SYSTEM_INSTRUCTION = """
You are HealthLink AI, a helpful healthcare assistant. Keep responses SHORT and CONCISE (2-3 paragraphs max).

Rules:
1. Give brief, direct answers about health topics
2. Use bullet points when listing symptoms or tips
3. Always end with: "Consult a doctor for proper diagnosis."
4. For emergencies, say: "Call 911 immediately."
5. Don't prescribe medications - suggest seeing a doctor

Be friendly but keep it short. No lengthy explanations unless asked.
"""


# ============= Request/Response Models =============

class ChatMessage(BaseModel):
    role: str
    text: str

class ChatRequest(BaseModel):
    message: str
    history: Optional[List[ChatMessage]] = []
    user_id: Optional[str] = "default_user"

class ChatResponse(BaseModel):
    text: str
    sources: List[Dict[str, Any]] = []
    function_calls: Optional[List[Dict[str, Any]]] = None
    timestamp: Optional[str] = None
    
    class Config:
        # For Pydantic v1 compatibility
        arbitrary_types_allowed = True

class DocumentRequest(BaseModel):
    id: str
    content: str
    category: str = "general"

class FeedbackRequest(BaseModel):
    user_id: str = "default_user"
    rating: int
    comment: Optional[str] = ""
    message_id: Optional[str] = None

class RegisterRequest(BaseModel):
    username: str
    password: str
    email: Optional[str] = None

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    username: str
    is_admin: bool = False

class AppointmentRequest(BaseModel):
    user_id: str = "default_user"
    user_name: str
    user_email: str
    user_phone: str
    appointment_type: str = "General Consultation"
    preferred_date: str
    preferred_time: str
    notes: Optional[str] = ""

class AppointmentStatusUpdate(BaseModel):
    status: str  # pending, confirmed, cancelled

class HealthResponse(BaseModel):
    status: str
    ai_provider: Optional[str]
    ai_configured: bool
    rag_stats: Dict[str, Any]
    timestamp: Optional[str] = None
    
    class Config:
        arbitrary_types_allowed = True


# ============= AI Chat Functions =============

async def chat_with_groq(message: str, context: str, history: List[ChatMessage]) -> str:
    """Chat using Groq API"""
    messages = [{"role": "system", "content": SYSTEM_INSTRUCTION}]
    
    # Add history
    for msg in history:
        role = "assistant" if msg.role == "model" else msg.role
        messages.append({"role": role, "content": msg.text})
    
    # Build augmented message
    if context:
        augmented_message = f"""RELEVANT HEALTHCARE INFORMATION:
{context}

USER QUESTION: {message}

Please answer the user's question using the relevant healthcare information provided above. If the information is helpful, incorporate it into your response. Always include appropriate medical disclaimers."""
    else:
        augmented_message = message
    
    messages.append({"role": "user", "content": augmented_message})
    
    response = ai_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        max_tokens=1024,
        temperature=0.7,
    )
    
    return response.choices[0].message.content


async def chat_with_gemini(message: str, context: str, history: List[ChatMessage]) -> str:
    """Chat using Gemini API (google-generativeai)"""
    # Build the full prompt with system instruction and context
    full_prompt = SYSTEM_INSTRUCTION + "\n\n"
    
    # Add conversation history
    for msg in history:
        role_label = "User" if msg.role == "user" else "Assistant"
        full_prompt += f"{role_label}: {msg.text}\n\n"
    
    # Build augmented message
    if context:
        full_prompt += f"""RELEVANT HEALTHCARE INFORMATION:
{context}

USER QUESTION: {message}

Please answer the user's question using the relevant healthcare information provided above. If the information is helpful, incorporate it into your response. Always include appropriate medical disclaimers."""
    else:
        full_prompt += f"User: {message}"
    
    try:
        response = gemini_model.generate_content(full_prompt)
        return response.text or "I'm sorry, I couldn't process that. Please try again."
    except Exception as e:
        logger.error(f"Gemini API error: {e}")
        return "I'm experiencing technical difficulties. Please try again."


# ============= Application Lifecycle =============

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for startup and shutdown"""
    # Startup
    logger.info("Starting HealthLink AI Backend...")
    rag_service = get_rag_service()
    stats = rag_service.get_stats()
    logger.info(f"RAG Service ready with {stats['total_documents']} documents")
    
    if not ai_client:
        logger.warning("No AI API configured. Set GROQ_API_KEY or GEMINI_API_KEY.")
    else:
        logger.info(f"AI Provider: {ai_provider}")
    
    yield
    
    # Shutdown
    logger.info("Shutting down HealthLink AI Backend...")


# ============= FastAPI Application =============

app = FastAPI(
    title="HealthLink AI Backend",
    description="RAG-powered healthcare assistant API with Groq and Gemini support",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=False,  # Must be False when using wildcard origins
    allow_methods=["GET", "POST", "OPTIONS", "PUT", "DELETE"],
    allow_headers=["*"],
)


# ============= Security Middleware =============

@app.middleware("http")
async def security_middleware(request: Request, call_next):
    """Add security headers and rate limiting"""
    # Get client IP
    client_ip = request.client.host if request.client else "unknown"
    
    # Rate limiting (60 requests per minute)
    allowed, message = security_manager.check_rate_limit(client_ip, limit=60, window=60)
    if not allowed:
        log_event("RATE_LIMIT_EXCEEDED", client_ip, f"Path: {request.url.path}")
        return JSONResponse(
            status_code=429,
            content={"error": message, "status_code": 429}
        )
    
    # Process request
    response = await call_next(request)
    
    # Add security headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    
    return response


# ============= Error Handlers =============

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "status_code": exc.status_code}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "status_code": 500}
    )


# ============= API Endpoints =============

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "HealthLink AI Backend is running",
        "status": "healthy",
        "ai_provider": ai_provider or "none",
        "version": "2.0.0"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    rag_service = get_rag_service()
    return {
        "status": "healthy",
        "ai_provider": ai_provider,
        "ai_configured": bool(ai_client),
        "rag_stats": rag_service.get_stats(),
        "timestamp": datetime.now().isoformat()
    }


@app.post("/chat")
async def chat(request: ChatRequest):
    """Main chat endpoint with RAG"""
    if not ai_client:
        raise HTTPException(
            status_code=500, 
            detail="No AI API configured. Set GROQ_API_KEY or GEMINI_API_KEY."
        )
    
    logger.info(f"Chat request from user: {request.user_id}")
    
    # Save user message
    _save_history(request.user_id, request.message, "user")
    
    rag_service = get_rag_service()
    
    # Get relevant context from RAG
    context = rag_service.get_augmented_context(request.message, n_results=3)
    retrieved_docs = rag_service.query(request.message, n_results=3)
    
    try:
        # Call appropriate AI API
        if ai_provider == "groq":
            response_text = await chat_with_groq(request.message, context, request.history or [])
        else:
            response_text = await chat_with_gemini(request.message, context, request.history or [])
        
        # Save assistant response
        _save_history(request.user_id, response_text, "assistant")
        
        # Format sources for frontend - show ALL sources
        sources = []
        for doc in retrieved_docs:
            metadata = doc.get("metadata", {})
            relevance = 0
            if doc.get("distance") is not None:
                relevance = round((1 - doc["distance"]) * 100, 1)
            
            # Get content snippet (first 150 chars)
            content = doc.get("content", "")
            snippet = content[:150] + "..." if len(content) > 150 else content
            
            source = {
                "category": metadata.get("category", "general"),
                "url": metadata.get("url", ""),
                "source": metadata.get("source", "") or ("Disease Symptoms Database" if metadata.get("category") == "diseases" else "Healthcare Knowledge Base"),
                "relevance": relevance,
                "snippet": snippet
            }
            sources.append(source)
            logger.info(f"Source: {source['source']} - Relevance: {relevance}%")
        
        logger.info(f"Returning {len(sources)} sources")
        
        logger.info(f"Successfully generated response for user: {request.user_id}")
        
        return {
            "text": response_text,
            "sources": sources,
            "function_calls": None,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"AI API Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"AI processing error: {str(e)}")


@app.post("/embed")
async def embed_document(request: DocumentRequest):
    """Add a new document to the knowledge base"""
    rag_service = get_rag_service()
    
    success = rag_service.add_document(
        doc_id=request.id,
        content=request.content,
        category=request.category
    )
    
    if success:
        logger.info(f"Document {request.id} added successfully")
        return {"status": "success", "message": f"Document {request.id} added successfully"}
    else:
        raise HTTPException(status_code=500, detail="Failed to add document")


@app.post("/feedback")
async def submit_feedback(request: FeedbackRequest):
    """Submit user feedback"""
    logger.info(f"Feedback received from {request.user_id}: rating={request.rating}")
    
    feedback_data = {
        "user_id": request.user_id,
        "rating": request.rating,
        "comment": request.comment,
        "timestamp": datetime.now().isoformat()
    }
    _save_feedback(feedback_data)
    
    return {
        "status": "success",
        "message": "Thank you for your feedback!",
        "rating": request.rating
    }


@app.get("/admin/feedback")
async def get_admin_feedback():
    """Get all feedback (Admin)"""
    return {"feedback": _load_feedback()}


# ============= Appointment Endpoints =============

@app.post("/appointments")
async def create_appointment(request: AppointmentRequest):
    """Book a new appointment"""
    appointment_data = {
        "user_id": request.user_id,
        "user_name": request.user_name,
        "user_email": request.user_email,
        "user_phone": request.user_phone,
        "appointment_type": request.appointment_type,
        "preferred_date": request.preferred_date,
        "preferred_time": request.preferred_time,
        "notes": request.notes
    }
    
    appointment_id = _save_appointment(appointment_data)
    
    if appointment_id > 0:
        return {
            "status": "success",
            "message": "Appointment booked successfully!",
            "appointment_id": appointment_id
        }
    else:
        raise HTTPException(status_code=500, detail="Failed to book appointment")

@app.get("/appointments/{user_id}")
async def get_user_appointments(user_id: str):
    """Get all appointments for a specific user"""
    appointments = _get_user_appointments(user_id)
    return {"appointments": appointments}

@app.get("/admin/appointments")
async def get_all_appointments():
    """Get all appointments (Admin)"""
    appointments = _get_all_appointments()
    return {"appointments": appointments}

@app.put("/appointments/{appointment_id}")
async def update_appointment_status(appointment_id: int, request: AppointmentStatusUpdate):
    """Update the status of an appointment"""
    success = _update_appointment_status(appointment_id, request.status)
    
    if success:
        return {
            "status": "success",
            "message": f"Appointment status updated to {request.status}"
        }
    else:
        raise HTTPException(status_code=404, detail="Appointment not found")


@app.delete("/appointments/{appointment_id}")
async def delete_appointment(appointment_id: int):
    """Delete an appointment (admin only)"""
    try:
        from persistence import SessionLocal
        from db_manager import Appointment
        
        db = SessionLocal()
        appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
        
        if appointment:
            db.delete(appointment)
            db.commit()
            db.close()
            
            log_event("APPOINTMENT_DELETED", "admin", f"Deleted appointment ID: {appointment_id}")
            
            return {
                "status": "success",
                "message": f"Appointment {appointment_id} deleted successfully"
            }
        else:
            db.close()
            raise HTTPException(status_code=404, detail="Appointment not found")
    except Exception as e:
        logger.error(f"Error deleting appointment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/admin/feedback")
async def get_admin_feedback():
    """Get all feedback for admin dashboard"""
    try:
        feedback = _load_feedback()
        return {
            "status": "success",
            "feedback": feedback
        }
    except Exception as e:
        logger.error(f"Error loading feedback: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============= Auth Endpoints =============

@app.post("/auth/register")
async def register(request: RegisterRequest, req: Request):
    """Register a new user with input validation"""
    # Validate username
    username_valid, username_err = validate_username(request.username)
    if not username_valid:
        raise HTTPException(status_code=400, detail=username_err)
    
    # Validate password
    password_valid, password_err = validate_password(request.password)
    if not password_valid:
        raise HTTPException(status_code=400, detail=password_err)
    
    # Validate email if provided
    if request.email:
        email_valid, email_err = validate_email(request.email)
        if not email_valid:
            raise HTTPException(status_code=400, detail=email_err)
    
    # Sanitize inputs
    clean_username = sanitize(request.username, max_length=50)
    clean_email = sanitize(request.email, max_length=100) if request.email else None
    
    user = create_user(clean_username, request.password, clean_email)
    if not user:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    # Log successful registration
    client_ip = req.client.host if req.client else "unknown"
    log_event("USER_REGISTERED", clean_username, f"IP: {client_ip}")
    logger.info(f"New user registered: {clean_username}")
    
    # Create token for auto-login after registration
    token = create_access_token({"sub": str(user.id), "username": user.username})
    
    return {
        "status": "success",
        "message": "Registration successful",
        "access_token": token,
        "token_type": "bearer",
        "username": user.username,
        "is_admin": bool(user.is_admin)
    }


@app.post("/auth/login")
async def login(request: LoginRequest, req: Request):
    """Login with brute force protection"""
    client_ip = req.client.host if req.client else "unknown"
    
    # Check for brute force attempts
    allowed, message = security_manager.track_failed_login(request.username)
    if not allowed:
        log_event("ACCOUNT_LOCKED", request.username, f"IP: {client_ip}")
        raise HTTPException(status_code=429, detail=message)
    
    user = authenticate_user(request.username, request.password)
    if not user:
        security_manager.log_authentication(request.username, False, client_ip)
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    # Clear failed attempts on successful login
    security_manager.clear_failed_attempts(request.username)
    security_manager.log_authentication(request.username, True, client_ip)
    
    token = create_access_token({"sub": str(user.id), "username": user.username})
    logger.info(f"User logged in: {request.username}")
    
    return {
        "access_token": token,
        "token_type": "bearer",
        "username": user.username,
        "is_admin": bool(user.is_admin)
    }


@app.get("/auth/me")
async def get_current_user(token: str):
    """Get current user info from token"""
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    user_id = payload.get("sub")
    user = get_user_by_id(int(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "is_admin": bool(user.is_admin)
    }


@app.get("/stats")
async def get_stats():
    """Get knowledge base statistics"""
    rag_service = get_rag_service()
    return rag_service.get_stats()


@app.post("/clear-context")
async def clear_context(user_id: str = "default_user"):
    """Clear user context (for new conversation)"""
    logger.info(f"Clearing context for user: {user_id}")
    # Context is managed per-request via history, so this is a no-op
    # But we keep the endpoint for frontend compatibility
    return {
        "status": "success",
        "message": "Context cleared successfully"
    }


@app.get("/history/recent")
async def get_recent_history(user_id: str = "default_user"):
    """Get recent chat history"""
    history = _get_history(user_id)
    
    # Format for frontend
    formatted_history = []
    # Identify pairs of user/assistant messages
    # This is a simple approximation
    for i in range(len(history)):
        msg = history[i]
        if msg['role'] == 'user':
            user_msg = msg['message']
            bot_msg = ""
            # Try to find next assistant message
            if i + 1 < len(history) and history[i+1]['role'] == 'assistant':
                bot_msg = history[i+1]['message']
            
            if bot_msg: # Only add if we have a pair (implied) or just show user
                formatted_history.append({
                    "id": f"hist_{i}",
                    "user_message": user_msg,
                    "bot_message": bot_msg,
                    "timestamp": msg.get('timestamp')
                })
    
    return {
        "status": "success",
        "history": formatted_history,
        "messages": history
    }


# ============= Main Entry Point =============

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)
