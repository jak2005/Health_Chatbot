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
    
    # Appointments Section
    with st.expander("📅 Appointments"):
        if st.button("📋 Book Appointment", use_container_width=True, key="book_apt_btn"):
            st.session_state.view_mode = 'appointments'
            st.rerun()
        if st.button("📆 My Appointments", use_container_width=True, key="my_apt_btn"):
            st.session_state.view_mode = 'my_appointments'
            st.rerun()
    
    # User Account Section
    with st.expander("👤 Account"):
        if st.session_state.logged_in_user:
            # Logged in state
            st.success(f"✅ Welcome, **{st.session_state.logged_in_user}**!")
            if st.session_state.is_admin:
                st.caption("🔑 Admin Account")
            
            if st.button("🚪 Logout", use_container_width=True, key="logout_btn"):
                logout_user()
                st.rerun()
        else:
            # Login/Register tabs
            auth_tab = st.radio("", ["🔑 Login", "📝 Register"], horizontal=True, key="auth_tab", label_visibility="collapsed")
            
            if auth_tab == "🔑 Login":
                login_username = st.text_input("Username", key="login_user", placeholder="Enter username")
                login_password = st.text_input("Password", type="password", key="login_pass", placeholder="Enter password")
                
                if st.button("Login", use_container_width=True, key="login_btn", type="primary"):
                    if login_username and login_password:
                        success, msg = login_user(login_username, login_password)
                        if success:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
                    else:
                        st.warning("Please enter username and password")
            
            else:  # Register
                reg_username = st.text_input("Username", key="reg_user", placeholder="Choose username")
                reg_email = st.text_input("Email (optional)", key="reg_email", placeholder="your@email.com")
                reg_password = st.text_input("Password", type="password", key="reg_pass", placeholder="Choose password")
                reg_confirm = st.text_input("Confirm Password", type="password", key="reg_confirm", placeholder="Repeat password")
                
                if st.button("Create Account", use_container_width=True, key="reg_btn", type="primary"):
                    if reg_username and reg_password:
                        if reg_password != reg_confirm:
                            st.error("Passwords don't match!")
                        elif len(reg_password) < 4:
                            st.warning("Password must be at least 4 characters")
                        else:
                            success, msg = register_user(reg_username, reg_password, reg_email if reg_email else None)
                            if success:
                                st.success("🎉 Account created successfully!")
                                st.rerun()
                            else:
                                st.error(msg)
                    else:
                        st.warning("Please enter username and password")
    
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
                apt_table = []
                for apt in all_appointments:
                    apt_table.append({
                        "Date": apt.get('preferred_date', ''),
                        "Time": apt.get('preferred_time', ''),
                        "Name": apt.get('user_name', ''),
                        "Email": apt.get('user_email', ''),
                        "Phone": apt.get('user_phone', ''),
                        "Type": apt.get('appointment_type', ''),
                        "Status": apt.get('status', '').title()
                    })
                
                st.dataframe(
                    apt_table,
                    column_config={
                        "Status": st.column_config.TextColumn(
                            "Status",
                            help="pending/confirmed/cancelled"
                        ),
                    },
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info("No appointments booked yet.")
    except Exception as e:
        st.warning(f"Could not load appointments: {e}")

elif st.session_state.view_mode == 'appointments':
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