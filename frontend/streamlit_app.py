# frontend/streamlit_app.py
"""
HealthLink AI - Streamlit Frontend
Connects to FastAPI backend for healthcare AI chat
"""

import streamlit as st
import requests
import json
from datetime import datetime
import time
import os

# Configure Streamlit page
st.set_page_config(
    page_title="HealthCare AI - Health Assistant",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

import utils
utils.load_css()

# Constants - Use Streamlit secrets for production, fallback to env/localhost for development
try:
    API_URL = st.secrets["API_URL"]
except (KeyError, FileNotFoundError):
    API_URL = os.environ.get('API_URL', 'http://localhost:8080')

# Ensure API_URL has proper protocol
if API_URL and not API_URL.startswith('http'):
    API_URL = f"https://{API_URL}"

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []
if 'user_id' not in st.session_state:
    st.session_state.user_id = "local_user"
if 'session_start' not in st.session_state:
    st.session_state.session_start = datetime.now()
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'view_mode' not in st.session_state:
    st.session_state.view_mode = 'chat'

# Auth session state
if 'auth_token' not in st.session_state:
    st.session_state.auth_token = None
if 'logged_in_user' not in st.session_state:
    st.session_state.logged_in_user = None
if 'is_admin' not in st.session_state:
    st.session_state.is_admin = False
if 'auth_mode' not in st.session_state:
    st.session_state.auth_mode = 'login'  # 'login' or 'register'


def check_backend_health():
    """Check if backend is available"""
    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        return response.status_code == 200
    except Exception:
        return False


def get_chat_history():
    """Get chat history from session state (managed client-side)"""
    # History is now managed client-side via session state
    history = []
    messages = st.session_state.messages
    
    # Group messages into chat pairs
    for i in range(0, len(messages) - 1, 2):
        if i + 1 < len(messages):
            user_msg = messages[i]
            bot_msg = messages[i + 1]
            if user_msg.get('role') == 'user' and bot_msg.get('role') == 'assistant':
                history.append({
                    'id': f"chat_{i}",
                    'user_message': user_msg.get('content', ''),
                    'bot_message': bot_msg.get('content', ''),
                    'timestamp': datetime.now().isoformat()
                })
    
    return history


def get_all_feedback():
    """Fetch all feedback (Admin only)"""
    try:
        response = requests.get(f"{API_URL}/admin/feedback", timeout=10)
        if response.status_code == 200:
            return response.json().get('feedback', [])
        return []
    except Exception as e:
        st.error(f"Error fetching feedback: {str(e)}")
        return []


def send_message(message):
    """Send chat message to FastAPI backend"""
    try:
        # Build history for context (convert to ChatMessage format)
        history = []
        for msg in st.session_state.messages:
            role = "model" if msg["role"] == "assistant" else msg["role"]
            history.append({
                "role": role,
                "text": msg["content"]
            })
        
        response = requests.post(
            f"{API_URL}/chat",
            json={
                "user_id": st.session_state.user_id,
                "message": message,
                "history": history
            },
            timeout=60
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"API Error: {response.status_code}")
            return None
            
    except requests.exceptions.Timeout:
        st.error("Request timed out. Please try again.")
        return None
    except Exception as e:
        st.error(f"Error sending message: {str(e)}")
        return None


def submit_feedback(rating, comment):
    """Submit user feedback to API"""
    try:
        response = requests.post(
            f"{API_URL}/feedback",
            json={
                "user_id": st.session_state.user_id,
                "rating": rating,
                "comment": comment
            },
            timeout=10
        )
        return response.json()
    except Exception as e:
        st.error(f"Error submitting feedback: {str(e)}")
        return None


def clear_chat_context():
    """Clear chat context"""
    try:
        response = requests.post(
            f"{API_URL}/clear-context",
            params={"user_id": st.session_state.user_id},
            timeout=10
        )
        if response.status_code == 200:
            st.session_state.messages = []
            st.session_state.chat_history = []
            return True
    except Exception as e:
        st.error(f"Error clearing context: {str(e)}")
    return False


def register_user(username, password, email=None):
    """Register a new user"""
    try:
        response = requests.post(
            f"{API_URL}/auth/register",
            json={"username": username, "password": password, "email": email},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            st.session_state.auth_token = data.get('access_token')
            st.session_state.logged_in_user = data.get('username')
            st.session_state.is_admin = data.get('is_admin', False)
            st.session_state.user_id = data.get('username')
            return True, "Registration successful!"
        else:
            error = response.json().get('detail', 'Registration failed')
            return False, error
    except Exception as e:
        return False, str(e)


def login_user(username, password):
    """Login user"""
    try:
        response = requests.post(
            f"{API_URL}/auth/login",
            json={"username": username, "password": password},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            st.session_state.auth_token = data.get('access_token')
            st.session_state.logged_in_user = data.get('username')
            st.session_state.is_admin = data.get('is_admin', False)
            st.session_state.user_id = data.get('username')
            return True, "Login successful!"
        else:
            error = response.json().get('detail', 'Login failed')
            return False, error
    except Exception as e:
        return False, str(e)


def logout_user():
    """Logout user"""
    st.session_state.auth_token = None
    st.session_state.logged_in_user = None
    st.session_state.is_admin = False
    st.session_state.user_id = "local_user"
    st.session_state.messages = []
    st.session_state.view_mode = 'chat'


# Sidebar
with st.sidebar:
    st.title("🏥 HealthCare AI")
    
    # New Chat Button
    if st.button("➕ New Chat", key="new_chat", use_container_width=True):
        st.session_state.view_mode = 'chat'
        st.session_state.admin_password = "" # Clear password for logout
        if clear_chat_context():
            st.rerun()

    st.markdown("---")

    # Admin Section
    with st.expander("🔐 Admin Access"):
        if st.session_state.view_mode == 'admin':
            st.success("✅ Admin Dashboard Active")
            if st.button("🚪 Exit Admin Mode", use_container_width=True):
                st.session_state.view_mode = 'chat'
                st.session_state.admin_password = "" 
                st.rerun()
        else:
            password = st.text_input("Password", type="password", key="admin_password")
            if password == "admin123":
                st.session_state.view_mode = 'admin'
                st.rerun()
            elif password:
                st.error("Incorrect password")
    
    st.markdown("---")
    
    # Recent Chat History
    st.caption("Your chats") 
    history = get_chat_history()
    if history:
        for chat in history[-10:]:  # Show last 10 chats
            msg = chat.get('user_message', 'Unknown')
            if len(msg) > 30:
                msg = msg[:27] + "..."
            
            if st.button(f"💬 {msg}", key=f"hist_{chat['id']}", use_container_width=True):
                with st.expander("View Chat", expanded=True):
                    st.markdown(f"**You:** {chat.get('user_message')}")
                    st.markdown(f"**Assistant:** {chat.get('bot_message')}")
    else:
        st.caption("No history yet. Start a conversation!")
    
    st.markdown("---")
    
    # Feedback section
    st.subheader("📝 Feedback")
    rating = st.slider("Rate your experience", 1, 5, 3)
    feedback_comment = st.text_area("Your feedback", placeholder="Share your thoughts...")
    if st.button("Submit Feedback", use_container_width=True):
        result = submit_feedback(rating, feedback_comment)
        if result and result.get('status') == 'success':
            st.success("Thank you for your feedback!")
        else:
            st.warning("Could not submit feedback.")



if st.session_state.view_mode == 'admin':
    st.title("📊 Admin Dashboard")
    
    # Backend status indicator
    if check_backend_health():
        st.success("✅ Backend Connected")
    else:
        st.error("❌ Backend Offline")
    
    col1, col2 = st.columns([1, 6])
    with col1:
        if st.button("⬅️ Back"):
            st.session_state.view_mode = 'chat'
            st.session_state.admin_password = "" # Clear password
            st.rerun()
            
    st.markdown("---")
    st.subheader("User Feedback Overview")
    
    col_a, col_b = st.columns([4, 1])
    with col_b:
        if st.button("🔄 Refresh"):
            st.rerun()
            
    feedback_data = get_all_feedback()
    
    if feedback_data:
        # Prepare data for dataframe
        table_data = []
        for item in feedback_data:
            table_data.append({
                "Date": item.get('timestamp', '').split('T')[0],
                "User ID": item.get('user_id', 'Unknown'),
                "Rating": item.get('rating', 0),
                "Feedback": item.get('comment', '')
            })
            
        st.dataframe(
            table_data,
            column_config={
                "Rating": st.column_config.NumberColumn(
                    "Rating",
                    help="User rating (1-5)",
                    format="%d ⭐",
                ),
                "Feedback": st.column_config.TextColumn(
                    "Feedback",
                    width="large"
                ),
            },
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No feedback received yet.")

else:
    # Main chat interface
    st.title("💬 Chat with HealthCare AI")
    st.caption("Your AI-powered healthcare assistant. Ask me about health tips, symptoms, or general wellness advice.")
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
            # Show sources if available
            if message.get("sources"):
                with st.expander("📚 Sources"):
                    for source in message["sources"]:
                        url = source.get('url', '')
                        source_name = source.get('source', 'Healthcare Resource')
                        if url:
                            # Extract topic name from URL (e.g., /glossary/affordability-exemption/ -> Affordability Exemption)
                            topic = url.rstrip('/').split('/')[-1].replace('-', ' ').title()
                            st.markdown(f"🔗 [{topic}]({url}) - {source_name}")
                        else:
                            # Fallback if no URL
                            category = source.get('category', 'general')
                            st.markdown(f"📄 {source_name} ({category.title()})")
    
    # Chat input
    if prompt := st.chat_input("How can I help you today?"):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
    
        # Show thinking indicator
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                # Get bot response
                response = send_message(prompt)
        
            if response:
                assistant_response = response.get('text', response.get('response', "I'm sorry, I couldn't process that request."))
                sources = response.get('sources', [])
                
                # Add assistant response to chat history
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": assistant_response,
                    "sources": sources
                })
                
                st.markdown(assistant_response)
                
                # Show sources
                if sources:
                    with st.expander("📚 Sources"):
                        for source in sources:
                            url = source.get('url', '')
                            source_name = source.get('source', 'Healthcare Resource')
                            if url:
                                # Extract topic name from URL (e.g., /glossary/affordability-exemption/ -> Affordability Exemption)
                                topic = url.rstrip('/').split('/')[-1].replace('-', ' ').title()
                                st.markdown(f"🔗 [{topic}]({url}) - {source_name}")
                            else:
                                # Fallback if no URL
                                category = source.get('category', 'general')
                                st.markdown(f"📄 {source_name} ({category.title()})")
            else:
                error_msg = "I'm having trouble connecting to the server. Please try again."
                st.session_state.messages.append({"role": "assistant", "content": error_msg})
                st.markdown(error_msg)

# Footer