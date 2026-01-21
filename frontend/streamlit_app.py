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

# PWA Support - Add meta tags for mobile app installation
pwa_meta = """
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="HealthCare AI">
<meta name="theme-color" content="#4CAF50">
<meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
<link rel="manifest" href="data:application/json;base64,ewogICJuYW1lIjogIkhlYWx0aENhcmUgQUkiLAogICJzaG9ydF9uYW1lIjogIkhlYWx0aEFJIiwKICAiZGVzY3JpcHRpb24iOiAiWW91ciBBSS1wb3dlcmVkIGhlYWx0aGNhcmUgYXNzaXN0YW50IiwKICAic3RhcnRfdXJsIjogIi8iLAogICJkaXNwbGF5IjogInN0YW5kYWxvbmUiLAogICJiYWNrZ3JvdW5kX2NvbG9yIjogIiMwRTExMTciLAogICJ0aGVtZV9jb2xvciI6ICIjNENBRjUwIiwKICAiaWNvbnMiOiBbCiAgICB7CiAgICAgICJzcmMiOiAiZGF0YTppbWFnZS9zdmcreG1sLCUzQ3N2ZyB4bWxucz0naHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmcnIHZpZXdCb3g9JzAgMCAxMDAgMTAwJyUzRSUzQ3RleHQgeT0nLjllbScgZm9udC1zaXplPSc5MCclM0UlRjAlOUYlOEYlQTUlM0MvdGV4dCUzRSUzQy9zdmclM0UiLAogICAgICAic2l6ZXMiOiAiYW55IiwKICAgICAgInR5cGUiOiAiaW1hZ2Uvc3ZnK3htbCIKICAgIH0KICBdCn0=">
<link rel="apple-touch-icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Ctext y='.9em' font-size='90'%3E🏥%3C/text%3E%3C/svg%3E">
"""
st.markdown(pwa_meta, unsafe_allow_html=True)

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
    st.session_state.view_mode = 'landing'  # Start with landing page

# Auth session state
if 'auth_token' not in st.session_state:
    st.session_state.auth_token = None
if 'logged_in_user' not in st.session_state:
    st.session_state.logged_in_user = None
if 'is_admin' not in st.session_state:
    st.session_state.is_admin = False
if 'user_role' not in st.session_state:
    st.session_state.user_role = "patient"  # patient or doctor
if 'user_specialty' not in st.session_state:
    st.session_state.user_specialty = None
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


def load_local_users():
    """Load users from local JSON (Prototype Mode)"""
    try:
        if os.path.exists('local_users.json'):
            with open('local_users.json', 'r') as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def save_local_user(username, data):
    """Save user to local JSON (Prototype Mode)"""
    users = load_local_users()
    users[username] = data
    try:
        with open('local_users.json', 'w') as f:
            json.dump(users, f)
        return True
    except Exception:
        return False

def register_user(username, password, email=None, role="patient", specialty=None):
    """Register a new user (Try API -> Fallback to Local Prototype)"""
    # 1. Try API
    try:
        response = requests.post(
            f"{API_URL}/auth/register",
            json={
                "username": username, 
                "password": password, 
                "email": email,
                "role": role,
                "specialty": specialty
            },
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            st.session_state.auth_token = data.get('access_token')
            st.session_state.logged_in_user = data.get('username')
            st.session_state.is_admin = data.get('is_admin', False)
            st.session_state.user_role = data.get('role', 'patient')
            return True, "Registration successful!"
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        # API Offline - Use Prototype Mode
        st.warning("⚠️ Backend unavailable. Using Offline Prototype Mode. Data may not persist.")
    
    # 2. Local Fallback (Prototype Mode)
    users = load_local_users()
    if username in users:
        return False, "Username already exists (Offline Mode)"
    
    # Create local user
    user_data = {
        "password": password, # In a real app, hash this!
        "email": email,
        "role": role,
        "specialty": specialty,
        "id": len(users) + 1,
        "is_admin": False
    }
    if save_local_user(username, user_data):
        st.session_state.auth_token = "mock_token"
        st.session_state.logged_in_user = username
        st.session_state.is_admin = False
        st.session_state.user_role = role
        st.session_state.user_specialty = specialty
        return True, "Registered in Prototype Mode"
    
    return False, "Registration failed"


def login_user(username, password):
    """Login user (Try API -> Fallback to Local Prototype)"""
    # 1. Try API
    try:
        response = requests.post(
            f"{API_URL}/auth/login",
            json={"username": username, "password": password},
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            st.session_state.auth_token = data.get('access_token')
            st.session_state.logged_in_user = data.get('username')
            st.session_state.is_admin = data.get('is_admin', False)
            st.session_state.user_role = data.get('role', 'patient')
            return True, "Login successful!"
    except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
        st.warning("⚠️ Backend unavailable. Using Offline Prototype Mode.")

    # 2. Local Fallback (Prototype Mode)
    users = load_local_users()
    if username in users:
        if users[username]['password'] == password:
            user = users[username]
            st.session_state.auth_token = "mock_token"
            st.session_state.logged_in_user = username
            st.session_state.is_admin = user.get('is_admin', False)
            st.session_state.user_role = user.get('role', 'patient')
            st.session_state.user_specialty = user.get('specialty')
            return True, "Login successful (Offline)"
        else:
            return False, "Invalid password"
    
    return False, "User not found (Offline Mode)"


def logout_user():
    """Logout user"""
    st.session_state.auth_token = None
    st.session_state.logged_in_user = None
    st.session_state.is_admin = False
    st.session_state.user_id = "local_user"
    st.session_state.user_role = "patient"
    st.session_state.user_specialty = None
    st.session_state.messages = []
    st.session_state.view_mode = 'chat'


def get_unread_message_count():
    """Get count of unread messages for current user"""
    if not st.session_state.auth_token or not st.session_state.user_id_num:
        return 0
    try:
        response = requests.get(
            f"{API_URL}/messages/conversations",
            params={"token": st.session_state.auth_token},
            timeout=3
        )
        if response.status_code == 200:
            conversations = response.json().get('conversations', [])
            total_unread = sum(c.get('unread', 0) for c in conversations)
            return total_unread
    except Exception:
        pass
    return 0


# Header Bar with Sign Up / Log In (shows when not logged in)
if not st.session_state.logged_in_user:
    # Simple header bar
    st.markdown("""
    <style>
    .header-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 10px 20px;
        background: linear-gradient(90deg, #1a1f2e 0%, #2d3548 100%);
        border-radius: 10px;
        margin-bottom: 20px;
    }
    .header-logo {
        color: #4CAF50;
        font-size: 1.5em;
        font-weight: bold;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .header-logo span { font-size: 1.2em; }
    </style>
    <div class="header-bar">
        <div class="header-logo">
            <span>🏥</span> HealthCare AI
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Sign Up / Log In buttons in columns at top
    col1, col2, col3, col4, col5 = st.columns([4, 1, 1, 0.5, 0.5])
    with col4:
        if st.button("Sign Up", key="header_signup"):
            st.session_state.view_mode = 'signup'
            st.rerun()
    with col5:
        if st.button("Log In", key="header_login", type="primary"):
            st.session_state.view_mode = 'login'
            st.rerun()


# Sign Up Page
if st.session_state.view_mode == 'signup' and not st.session_state.logged_in_user:
    st.markdown("""
    <style>
    section[data-testid="stSidebar"] { display: none; }
    </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<h1 style='text-align:center;'>🏥 Create Account</h1>", unsafe_allow_html=True)
        
        reg_username = st.text_input("Username", placeholder="Choose a username", key="su_user")
        reg_email = st.text_input("Email", placeholder="your@email.com", key="su_email")
        
        role_type = st.radio("I am a:", ["🏥 Patient", "👨‍⚕️ Doctor"], horizontal=True, key="su_role")
        selected_role = "patient" if "Patient" in role_type else "doctor"
        
        specialty = None
        if selected_role == "doctor":
            specialty = st.selectbox("Medical Specialty", 
                ["General Medicine", "Cardiology", "Dermatology", "Orthopedics", 
                 "Pediatrics", "Neurology", "Psychiatry", "Gynecology", "ENT", "Ophthalmology"], key="su_spec")
        
        reg_password = st.text_input("Password", type="password", placeholder="Min 6 characters", key="su_pass")
        reg_confirm = st.text_input("Confirm Password", type="password", key="su_confirm")
        
        if st.button("Create Account", use_container_width=True, type="primary", key="su_btn"):
            if reg_username and reg_password:
                if reg_password != reg_confirm:
                    st.error("Passwords don't match!")
                elif len(reg_password) < 6:
                    st.warning("Password must be at least 6 characters")
                else:
                    success, msg = register_user(reg_username, reg_password, reg_email, role=selected_role, specialty=specialty)
                    if success:
                        st.success(f"🎉 {selected_role.title()} account created!")
                        st.session_state.view_mode = 'chat'
                        st.rerun()
                    else:
                        st.error(msg)
            else:
                st.warning("Please fill in all required fields")
        
        if st.button("Already have an account? Log In", use_container_width=True, key="su_switch"):
            st.session_state.view_mode = 'login'
            st.rerun()
        
        if st.button("⬅️ Back to Chat", use_container_width=True, key="su_back"):
            st.session_state.view_mode = 'chat'
            st.rerun()
    
    st.stop()


# Login Page
elif st.session_state.view_mode == 'login' and not st.session_state.logged_in_user:
    st.markdown("""
    <style>
    section[data-testid="stSidebar"] { display: none; }
    </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("<h1 style='text-align:center;'>🏥 Welcome Back</h1>", unsafe_allow_html=True)
        
        login_username = st.text_input("Username", placeholder="Enter username", key="li_user")
        login_password = st.text_input("Password", type="password", placeholder="Enter password", key="li_pass")
        
        if st.button("Log In", use_container_width=True, type="primary", key="li_btn"):
            if login_username and login_password:
                success, msg = login_user(login_username, login_password)
                if success:
                    st.success("Welcome back!")
                    st.session_state.view_mode = 'chat'
                    st.rerun()
                else:
                    st.error(msg)
            else:
                st.warning("Please enter username and password")
        
        if st.button("Don't have an account? Sign Up", use_container_width=True, key="li_switch"):
            st.session_state.view_mode = 'signup'
            st.rerun()
        
        if st.button("⬅️ Back to Chat", use_container_width=True, key="li_back"):
            st.session_state.view_mode = 'chat'
            st.rerun()
    
    st.stop()


# Sidebar (shows after login)
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
    
    # Appointments Section - Requires Login
    with st.expander("📅 Appointments"):
        if st.session_state.logged_in_user:
            # User is logged in - show appointment buttons
            if st.button("📋 Book Appointment", use_container_width=True, key="book_apt_btn"):
                st.session_state.view_mode = 'appointments'
                st.rerun()
            if st.button("📆 My Appointments", use_container_width=True, key="my_apt_btn"):
                st.session_state.view_mode = 'my_appointments'
                st.rerun()
        else:
            # User not logged in - show login prompt
            st.warning("🔒 Please login to access appointments")
            st.caption("Create an account or login below")
    
    # Doctor Section - Only show for doctors
    if st.session_state.logged_in_user and st.session_state.user_role == "doctor":
        # Get unread count for doctors too
        unread_count = get_unread_message_count()
        dashboard_label = f"🩺 Doctor Dashboard ({unread_count} msgs)" if unread_count > 0 else "🩺 Doctor Dashboard"
        with st.expander(dashboard_label, expanded=True):
            if st.button("📋 Appointment Requests", use_container_width=True, key="doc_apt_btn"):
                st.session_state.view_mode = 'doctor_appointments'
                st.rerun()
            if st.button("👥 My Patients", use_container_width=True, key="doc_patients_btn"):
                st.session_state.view_mode = 'doctor_patients'
                st.rerun()
            # Messages button for doctors
            msg_btn_label = f"💬 Messages ({unread_count} new)" if unread_count > 0 else "💬 Messages"
            if st.button(msg_btn_label, use_container_width=True, key="doc_msg_btn"):
                st.session_state.view_mode = 'messages'
                st.rerun()
    
    # Messages Section - For patients too
    if st.session_state.logged_in_user and st.session_state.user_role == "patient":
        # Get unread count
        unread_count = get_unread_message_count()
        msg_label = f"💬 Messages ({unread_count})" if unread_count > 0 else "💬 Messages"
        with st.expander(msg_label, expanded=unread_count > 0):
            btn_label = f"📬 My Messages ({unread_count} new)" if unread_count > 0 else "📬 My Messages"
            if st.button(btn_label, use_container_width=True, key="patient_msg_btn"):
                st.session_state.view_mode = 'messages'
                st.rerun()
    
    # User Account Section - Only show when logged in
    if st.session_state.logged_in_user:
        with st.expander("👤 Account", expanded=True):
            # Determine role display
            if st.session_state.is_admin:
                role_display = "🔑 Admin"
                role_icon = "👑"
            elif st.session_state.user_role == "doctor":
                specialty = st.session_state.user_specialty or "General"
                role_display = f"👨‍⚕️ Doctor • {specialty}"
                role_icon = "🩺"
            else:
                role_display = "🏥 Patient"
                role_icon = "👤"
            
            # Logged in state - Show profile info
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #1e3a5f 0%, #2d5a87 100%); 
                        padding: 15px; border-radius: 12px; margin-bottom: 10px; text-align: center;">
                <div style="font-size: 2.5em;">{role_icon}</div>
                <div style="color: #4CAF50; font-weight: bold; font-size: 1.2em;">{st.session_state.logged_in_user}</div>
                <div style="color: #888; font-size: 0.9em;">{role_display}</div>
            </div>
            """, unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("👤 My Profile", use_container_width=True, key="profile_btn"):
                    st.session_state.view_mode = 'profile'
                    st.rerun()
            with col2:
                if st.button("🚪 Logout", use_container_width=True, key="logout_btn"):
                    logout_user()
                    st.rerun()
    
    # Data Protection Section
    with st.expander("🔒 Data Protection"):
        st.markdown("""
        **Your data is protected by:**
        
        ✅ **AES-256 Encryption**  
        _Emails, phones & notes are encrypted_
        
        ✅ **Rate Limiting**  
        _60 requests/minute max_
        
        ✅ **Brute Force Protection**  
        _Account locks after 5 failed logins_
        
        ✅ **Input Validation**  
        _XSS & injection prevention_
        
        ✅ **Audit Logging**  
        _All access is logged_
        """)
        st.caption("🔐 HIPAA-inspired security")
    
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
    
    # Admin Appointments Section
    st.markdown("---")
    st.subheader("📅 All Appointments")
    
    try:
        apt_response = requests.get(f"{API_URL}/admin/appointments", timeout=10)
        if apt_response.status_code == 200:
            all_appointments = apt_response.json().get('appointments', [])
            
            if all_appointments:
                # Show appointments with delete buttons
                for apt in all_appointments:
                    apt_id = apt.get('id')
                    status = apt.get('status', 'pending')
                    status_color = {"pending": "🟡", "confirmed": "🟢", "cancelled": "🔴"}.get(status, "⚪")
                    
                    col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 2, 1])
                    
                    with col1:
                        st.caption("📅 Date/Time")
                        st.write(f"{apt.get('preferred_date', '')} {apt.get('preferred_time', '')}")
                    
                    with col2:
                        st.caption("👤 Patient")
                        st.write(f"{apt.get('user_name', 'N/A')}")
                        st.caption(apt.get('user_email', ''))
                    
                    with col3:
                        st.caption("📞 Phone")
                        st.write(apt.get('user_phone', 'N/A'))
                    
                    with col4:
                        st.caption("📋 Type / Status")
                        st.write(f"{apt.get('appointment_type', '')} {status_color}")
                    
                    with col5:
                        st.caption("Actions")
                        if st.button("🗑️", key=f"del_apt_{apt_id}", help="Delete"):
                            try:
                                del_resp = requests.delete(f"{API_URL}/appointments/{apt_id}", timeout=10)
                                if del_resp.status_code == 200:
                                    st.success("Deleted!")
                                    st.rerun()
                                else:
                                    st.error("Failed")
                            except Exception as e:
                                st.error(str(e))
                    
                    st.markdown("---")
            else:
                st.info("No appointments booked yet.")
    except Exception as e:
        st.warning(f"Could not load appointments: {e}")

elif st.session_state.view_mode == 'appointments':
    # Check if user is logged in
    if not st.session_state.logged_in_user:
        st.error("🔒 **Please login to book an appointment**")
        st.info("Go to the sidebar → Account → Login or Register")
        if st.button("⬅️ Back to Chat"):
            st.session_state.view_mode = 'chat'
            st.rerun()
        st.stop()
    
    # Appointment Booking Page - Beautiful Design
    st.markdown("""
    <style>
    .booking-header {
        background: linear-gradient(135deg, #4CAF50 0%, #2196F3 100%);
        border-radius: 16px;
        padding: 30px;
        margin-bottom: 24px;
        text-align: center;
    }
    .booking-header h2 { color: white; margin: 0; font-size: 2em; }
    .booking-header p { color: rgba(255,255,255,0.9); margin: 8px 0 0 0; }
    .section-card {
        background: linear-gradient(135deg, #1a1f2e 0%, #2d3548 100%);
        border-radius: 12px;
        padding: 20px;
        margin: 16px 0;
    }
    .section-title { color: #4CAF50; font-weight: 600; margin-bottom: 16px; font-size: 1.1em; }
    </style>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 6])
    with col1:
        if st.button("⬅️ Back", use_container_width=True):
            st.session_state.view_mode = 'chat'
            st.rerun()
    
    st.markdown("""
    <div class="booking-header">
        <h2>📅 Book an Appointment</h2>
        <p>Schedule your healthcare visit in just a few steps</p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.form("appointment_form"):
        # Contact Information Section
        st.markdown('<div class="section-title">👤 Contact Information</div>', unsafe_allow_html=True)
        col_a, col_b, col_c = st.columns(3)
        
        with col_a:
            user_name = st.text_input("Full Name *", placeholder="John Doe")
        with col_b:
            user_email = st.text_input("Email *", placeholder="john@example.com")
        with col_c:
            user_phone = st.text_input("Phone *", placeholder="+1 234 567 8900")
        
        st.markdown("---")
        
        # Appointment Details Section  
        st.markdown('<div class="section-title">🏥 Appointment Details</div>', unsafe_allow_html=True)
        col_d, col_e, col_f = st.columns(3)
        
        with col_d:
            appointment_type = st.selectbox(
                "Type *",
                ["🩺 General Consultation", "👨‍⚕️ Specialist Referral", "🧠 Mental Health", 
                 "📋 Follow-up Visit", "💉 Vaccination", "🧪 Lab Work", "📝 Other"]
            )
        
        with col_e:
            from datetime import date, timedelta
            min_date = date.today() + timedelta(days=1)
            preferred_date = st.date_input("Date *", min_value=min_date)
        
        with col_f:
            preferred_time = st.selectbox(
                "Time *",
                ["🌅 09:00 AM", "🌅 10:00 AM", "🌅 11:00 AM", "☀️ 12:00 PM", 
                 "☀️ 02:00 PM", "☀️ 03:00 PM", "🌆 04:00 PM", "🌆 05:00 PM"]
            )
        
        # Department and Doctor Selection
        col_dept, col_doc = st.columns(2)
        with col_dept:
            department = st.selectbox(
                "🏥 Department *",
                ["General Medicine", "Cardiology", "Dermatology", "Orthopedics", 
                 "Pediatrics", "Neurology", "Psychiatry", "Gynecology", "ENT", "Ophthalmology"]
            )
        with col_doc:
            # Doctors based on department - use session state to persist across reruns
            if 'doctor_options' not in st.session_state or st.session_state.get('last_department') != department:
                doctor_options = {"Any Available Doctor": None}
                try:
                    doc_resp = requests.get(f"{API_URL}/doctors", timeout=5)
                    if doc_resp.status_code == 200:
                        all_doctors = doc_resp.json().get('doctors', [])
                        # Filter by department (case-insensitive match)
                        dept_doctors = [d for d in all_doctors if d.get('specialty', '').lower() == department.lower()]
                        if dept_doctors:
                            doctor_options = {f"Dr. {d['username']} ({d['specialty']})": d['id'] for d in dept_doctors}
                        elif all_doctors:
                            # If no exact match, show all doctors with specialty info
                            doctor_options = {f"Dr. {d['username']} ({d['specialty']})": d['id'] for d in all_doctors}
                except Exception as e:
                    st.warning(f"Could not load doctors: {e}")
                # Store in session state
                st.session_state.doctor_options = doctor_options
                st.session_state.last_department = department
            else:
                doctor_options = st.session_state.doctor_options
            
            selected_doc_name = st.selectbox(
                "👨‍⚕️ Preferred Doctor",
                list(doctor_options.keys()),
                key="preferred_doctor"
            )
            selected_doc_id = doctor_options.get(selected_doc_name)
        
        st.markdown("---")
        
        # Notes Section
        st.markdown('<div class="section-title">📝 Additional Notes</div>', unsafe_allow_html=True)
        notes = st.text_area(
            "Describe your symptoms or reason for visit (optional)", 
            placeholder="Please share any relevant health information, symptoms, or questions you'd like to discuss...",
            height=100
        )
        
        st.markdown("")
        submit_btn = st.form_submit_button("✨ Book My Appointment", use_container_width=True, type="primary")
        
        if submit_btn:
            if user_name and user_email and user_phone:
                try:
                    # Clean up the appointment type and time (remove emojis for storage)
                    clean_type = appointment_type.split(" ", 1)[1] if " " in appointment_type else appointment_type
                    clean_time = preferred_time.split(" ", 1)[1] if " " in preferred_time else preferred_time
                    
                    response = requests.post(
                        f"{API_URL}/appointments",
                        json={
                            "user_id": st.session_state.get('user_id', 'default_user'),
                            "doctor_id": selected_doc_id,
                            "doctor_name": selected_doc_name,
                            "department": department,
                            "user_name": user_name,
                            "user_email": user_email,
                            "user_phone": user_phone,
                            "appointment_type": clean_type,
                            "preferred_date": str(preferred_date),
                            "preferred_time": clean_time,
                            "notes": notes
                        },
                        timeout=10
                    )
                    if response.status_code == 200:
                        st.success("🎉 Appointment booked successfully! We will contact you shortly to confirm.")
                        st.balloons()
                    else:
                        st.error("Failed to book appointment. Please try again.")
                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                st.warning("⚠️ Please fill in all required fields (*)")

elif st.session_state.view_mode == 'my_appointments':
    # Check if user is logged in
    if not st.session_state.logged_in_user:
        st.error("🔒 **Please login to view your appointments**")
        st.info("Go to the sidebar → Account → Login or Register")
        if st.button("⬅️ Back to Chat"):
            st.session_state.view_mode = 'chat'
            st.rerun()
        st.stop()
    
    # My Appointments Page - Beautiful Design
    st.markdown("""
    <style>
    .appointment-card {
        background: linear-gradient(135deg, #1a1f2e 0%, #2d3548 100%);
        border-radius: 16px;
        padding: 24px;
        margin: 16px 0;
        border-left: 4px solid #4CAF50;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }
    .appointment-card.pending { border-left-color: #FFC107; }
    .appointment-card.confirmed { border-left-color: #4CAF50; }
    .appointment-card.cancelled { border-left-color: #f44336; }
    .apt-type { font-size: 1.3em; font-weight: 600; color: #fff; margin-bottom: 12px; }
    .apt-detail { color: #b0b8c8; margin: 8px 0; font-size: 1em; }
    .apt-status { 
        display: inline-block; 
        padding: 4px 12px; 
        border-radius: 20px; 
        font-size: 0.85em; 
        font-weight: 500;
        margin-top: 12px;
    }
    .status-pending { background: rgba(255, 193, 7, 0.2); color: #FFC107; }
    .status-confirmed { background: rgba(76, 175, 80, 0.2); color: #4CAF50; }
    .status-cancelled { background: rgba(244, 67, 54, 0.2); color: #f44336; }
    </style>
    """, unsafe_allow_html=True)
    
    st.title("📆 My Appointments")
    st.caption("Manage your healthcare appointments")
    
    col1, col2, col3 = st.columns([1, 1, 5])
    with col1:
        if st.button("⬅️ Back", use_container_width=True):
            st.session_state.view_mode = 'chat'
            st.rerun()
    with col2:
        if st.button("🔄 Refresh", use_container_width=True):
            st.rerun()
    with col3:
        if st.button("➕ Book New", use_container_width=True, type="primary"):
            st.session_state.view_mode = 'appointments'
            st.rerun()
    
    st.markdown("---")
    
    try:
        user_id = st.session_state.get('user_id', 'default_user')
        response = requests.get(f"{API_URL}/appointments/{user_id}", timeout=10)
        
        if response.status_code == 200:
            appointments = response.json().get('appointments', [])
            
            if appointments:
                # Stats row
                total = len(appointments)
                pending = sum(1 for a in appointments if a['status'] == 'pending')
                confirmed = sum(1 for a in appointments if a['status'] == 'confirmed')
                
                stat1, stat2, stat3 = st.columns(3)
                stat1.metric("📋 Total", total)
                stat2.metric("🟡 Pending", pending)
                stat3.metric("🟢 Confirmed", confirmed)
                
                st.markdown("---")
                
                for apt in appointments:
                    status = apt['status']
                    status_emoji = {"pending": "🟡", "confirmed": "🟢", "cancelled": "🔴"}.get(status, "⚪")
                    status_class = f"status-{status}"
                    card_class = status
                    
                    # Beautiful card using columns
                    with st.container():
                        card_col1, card_col2 = st.columns([4, 1])
                        
                        with card_col1:
                            st.markdown(f"""
                            <div class="appointment-card {card_class}">
                                <div class="apt-type">{status_emoji} {apt['appointment_type']}</div>
                                <div class="apt-detail">📅 <strong>{apt['preferred_date']}</strong> at <strong>{apt['preferred_time']}</strong></div>
                                <div class="apt-detail">📝 {apt.get('notes', 'No additional notes')}</div>
                                <div class="apt-status {status_class}">{status.upper()}</div>
                            </div>
                            """, unsafe_allow_html=True)
                        
                        with card_col2:
                            if status == 'pending':
                                if st.button("❌ Cancel", key=f"cancel_{apt['id']}", use_container_width=True):
                                    try:
                                        cancel_resp = requests.put(
                                            f"{API_URL}/appointments/{apt['id']}",
                                            json={"status": "cancelled"},
                                            timeout=10
                                        )
                                        if cancel_resp.status_code == 200:
                                            st.rerun()
                                    except:
                                        pass
            else:
                st.markdown("""
                <div style="text-align: center; padding: 60px 20px;">
                    <div style="font-size: 4em; margin-bottom: 20px;">📭</div>
                    <h3 style="color: #888;">No appointments yet</h3>
                    <p style="color: #666;">Book your first appointment to get started!</p>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button("📋 Book Your First Appointment", use_container_width=True, type="primary"):
                    st.session_state.view_mode = 'appointments'
                    st.rerun()
        else:
            st.error("Could not load appointments")
    except Exception as e:
        st.error(f"Error loading appointments: {e}")


# Doctor Appointments View
elif st.session_state.view_mode == 'doctor_appointments':
    st.title("📋 Appointment Requests")
    
    col1, col2 = st.columns([1, 6])
    with col1:
        if st.button("⬅️ Back", key="doc_apt_back"):
            st.session_state.view_mode = 'chat'
            st.rerun()
    
    try:
        # Use params for token, headers for Authorization
        response = requests.get(f"{API_URL}/doctor/appointments", params={"token": st.session_state.auth_token})
        if response.status_code == 200:
            appointments = response.json().get('appointments', [])
            
            if not appointments:
                st.info("No appointment requests yet.")
            else:
                # Group by status
                pending = [a for a in appointments if a['status'] == 'pending']
                upcoming = [a for a in appointments if a['status'] == 'accepted']
                past = [a for a in appointments if a['status'] in ['completed', 'rejected', 'cancelled']]
                
                tab1, tab2, tab3 = st.tabs([f"🟡 Requests ({len(pending)})", f"🟢 Upcoming ({len(upcoming)})", "History"])
                
                with tab1:
                    for apt in pending:
                        with st.container():
                            st.markdown(f"""
                            <div style="background:#2d3548; padding:15px; border-radius:10px; margin-bottom:10px; border-left: 4px solid #FFC107;">
                                <h4>{apt['user_name']}</h4>
                                <p>📅 {apt['preferred_date']} at {apt['preferred_time']}</p>
                                <p>📝 {apt.get('notes', 'No notes')}</p>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            c1, c2, c3 = st.columns([1, 1, 1])
                            with c1:
                                if st.button("✅ Accept", key=f"acc_{apt['id']}"):
                                    requests.put(f"{API_URL}/appointments/{apt['id']}", json={"status": "accepted"})
                                    st.success("Accepted!")
                                    st.rerun()
                            with c2:
                                if st.button("❌ Reject", key=f"rej_{apt['id']}"):
                                    requests.put(f"{API_URL}/appointments/{apt['id']}", json={"status": "rejected"})
                                    st.warning("Rejected")
                                    st.rerun()
                            with c3:
                                if st.button("💬 Message", key=f"msg_req_{apt['id']}"):
                                    st.session_state.active_chat_partner = apt.get('patient_id')  # Use numerical ID
                                    st.session_state.active_chat_name = apt.get('user_name')
                                    st.session_state.view_mode = 'messages'
                                    st.rerun()
                
                with tab2:
                    for apt in upcoming:
                        st.markdown(f"""
                        <div style="background:#2d3548; padding:15px; border-radius:10px; margin-bottom:10px; border-left: 4px solid #4CAF50;">
                            <h4>{apt['user_name']}</h4>
                            <p>📅 {apt['preferred_date']} at {apt['preferred_time']}</p>
                            <p>📞 {apt['user_phone']} | 📧 {apt['user_email']}</p>
                            <p>📝 {apt.get('notes', 'No notes')}</p>
                        </div>
                        """, unsafe_allow_html=True)
                        btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 3])
                        with btn_col1:
                            if st.button("✅ Mark Completed", key=f"comp_{apt['id']}"):
                                requests.put(f"{API_URL}/appointments/{apt['id']}", json={"status": "completed"})
                                st.rerun()
                        with btn_col2:
                            if st.button("💬 Message", key=f"msg_{apt['id']}"):
                                st.session_state.active_chat_partner = apt.get('patient_id')  # Use numerical ID
                                st.session_state.active_chat_name = apt.get('user_name')
                                st.session_state.view_mode = 'messages'
                                st.rerun()
                            
                with tab3:
                    for apt in past:
                        color = "#f44336" if apt['status'] == 'rejected' else "#888"
                        st.markdown(f"""
                        <div style="background:#2d3548; padding:15px; border-radius:10px; margin-bottom:10px; border-left: 4px solid {color}; opacity: 0.7;">
                            <h4>{apt['user_name']} ({apt['status']})</h4>
                            <p>📅 {apt['preferred_date']}</p>
                        </div>
                        """, unsafe_allow_html=True)
        else:
            st.error("Could not load appointments")
    except Exception as e:
        st.error(f"Error: {e}")
    st.stop()


# Doctor Patients View
elif st.session_state.view_mode == 'doctor_patients':
    st.title("👥 My Patients")
    
    col1, col2 = st.columns([1, 6])
    with col1:
        if st.button("⬅️ Back", key="doc_pat_back"):
            st.session_state.view_mode = 'chat'
            st.rerun()
            
    try:
        response = requests.get(f"{API_URL}/doctor/patients", params={"token": st.session_state.auth_token})
        if response.status_code == 200:
            patients = response.json().get('patients', [])
            
            if not patients:
                st.info("No patients yet. Accept appointments to build your patient list.")
            else:
                for pat in patients:
                    with st.container():
                        c1, c2 = st.columns([3, 1])
                        with c1:
                            st.markdown(f"### 👤 {pat['user_name']}")
                            st.caption(f"Last visited: {pat['last_appointment']}")
                        with c2:
                            if st.button("💬 Chat", key=f"chat_{pat['user_id']}"):
                                st.session_state.active_chat_partner = pat.get('patient_id')  # Use numerical ID
                                st.session_state.active_chat_name = pat['user_name']
                                st.session_state.view_mode = 'messages'
                                st.rerun()
                        st.markdown("---")
        else:
            st.error("Could not load patients")
    except Exception as e:
        st.error(f"Error: {e}")
    st.stop()


# Messages View
elif st.session_state.view_mode == 'messages':
    st.title("💬 Messages")
    
    col1, col2 = st.columns([1, 6])
    with col1:
        if st.button("⬅️ Back", key="msg_back"):
            st.session_state.view_mode = 'chat'
            st.rerun()
    
    # Check if we have an active chat partner selected
    if 'active_chat_partner' in st.session_state and st.session_state.active_chat_partner:
        # Chat Interface
        partner_id = st.session_state.active_chat_partner
        partner_name = st.session_state.get('active_chat_name', f"User {partner_id}")
        
        st.subheader(f"Chat with {partner_name}")
        if st.button("🔙 All Conversations", key="back_conversations"):
             st.session_state.active_chat_partner = None
             st.rerun()
             
        # Load messages
        try:
            resp = requests.get(f"{API_URL}/messages/conversation/{partner_id}", params={"token": st.session_state.auth_token})
            if resp.status_code == 200:
                messages = resp.json().get('messages', [])
                
                # Message container
                chat_container = st.container()
                with chat_container:
                    if not messages:
                        st.info("No messages yet. Say hello!")
                    
                    current_user_id = st.session_state.get('user_id_num', 0)
                    for msg in messages:
                        is_me = msg['sender_id'] == int(current_user_id)
                        align = "right" if is_me else "left"
                        color = "#007bff" if is_me else "#444"
                        
                        st.markdown(f"""
                        <div style="display:flex; justify-content:{'flex-end' if is_me else 'flex-start'}; margin-bottom:10px;">
                            <div style="background:{color}; padding:10px 15px; border-radius:15px; max-width:70%;">
                                <div>{msg['content']}</div>
                                <div style="font-size:0.7em; opacity:0.7; margin-top:5px;">{msg['timestamp'].split('T')[1][:5]}</div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                
                # Input
                with st.form("msg_form", clear_on_submit=True):
                    new_msg = st.text_input("Type a message...", key="msg_input")
                    if st.form_submit_button("Send"):
                         if new_msg:
                             requests.post(f"{API_URL}/messages/send", 
                                json={"receiver_id": partner_id, "content": new_msg},
                                params={"token": st.session_state.auth_token})
                             st.rerun()
            else:
                st.error("Failed to load conversation")
        except Exception as e:
            st.error(f"Error: {e}")
            
    else:
        # Conversations List
        try:
            resp = requests.get(f"{API_URL}/messages/conversations", params={"token": st.session_state.auth_token})
            if resp.status_code == 200:
                convos = resp.json().get('conversations', [])
                
                if not convos:
                    st.info("No conversations yet.")
                else:
                    for c in convos:
                        with st.container():
                            col1, col2 = st.columns([4, 1])
                            with col1:
                                unread = f"🔴 {c['unread']}" if c['unread'] > 0 else ""
                                st.markdown(f"**{c['partner_name']}** {unread}")
                                st.caption(f"{c['last_message']} • {c['last_timestamp'].split('T')[0]}")
                            with col2:
                                if st.button("Open", key=f"open_{c['partner_id']}"):
                                    st.session_state.active_chat_partner = c['partner_id']
                                    st.session_state.active_chat_name = c['partner_name']
                                    st.rerun()
                            st.markdown("---")
            else:
                st.error("Failed to load conversations")
        except Exception as e:
            st.error(f"Error: {e}")
    
    st.stop()
    
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
                with st.expander("📚 Sources & References"):
                    for source in message["sources"]:
                        url = source.get('url', '')
                        source_name = source.get('source', 'Healthcare Resource')
                        relevance = source.get('relevance', 0)
                        snippet = source.get('snippet', '')
                        category = source.get('category', 'general')
                        
                        if url:
                            topic = url.rstrip('/').split('/')[-1].replace('-', ' ').title()
                            st.markdown(f"**🔗 [{topic}]({url})** - {source_name} ({relevance}% match)")
                        else:
                            st.markdown(f"**📄 {source_name}** ({category.title()}, {relevance}% match)")
                        
                        if snippet:
                            st.caption(f"_{snippet}_")
                        st.markdown("---")
    
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
                    with st.expander("📚 Sources & References", expanded=True):
                        for source in sources:
                            url = source.get('url', '')
                            source_name = source.get('source', 'Healthcare Resource')
                            relevance = source.get('relevance', 0)
                            snippet = source.get('snippet', '')
                            category = source.get('category', 'general')
                            
                            # Show source with relevance
                            if url:
                                topic = url.rstrip('/').split('/')[-1].replace('-', ' ').title()
                                st.markdown(f"**🔗 [{topic}]({url})** - {source_name} ({relevance}% match)")
                            else:
                                st.markdown(f"**📄 {source_name}** ({category.title()}, {relevance}% match)")
                            
                            # Show snippet if available
                            if snippet:
                                st.caption(f"_{snippet}_")
                            st.markdown("---")
            else:
                error_msg = "I'm having trouble connecting to the server. Please try again."
                st.session_state.messages.append({"role": "assistant", "content": error_msg})
                st.markdown(error_msg)

# Footer