import streamlit as st

def load_css():
    st.markdown("""
        <style>
        /* Sidebar Background - ChatGPT Dark */
        section[data-testid="stSidebar"] {
            background-color: #202123;
            color: #ececf1;
        }

        /* Sidebar Inputs & Text */
        section[data-testid="stSidebar"] .stMarkdown, 
        section[data-testid="stSidebar"] label,
        section[data-testid="stSidebar"] .stTextInput input {
            color: #ececf1 !important;
        }

        /* Main Area Background */
        .stApp {
            background-color: #343541;
        }

        /* Hide Streamlit Toolbar and Footer */
        .stDeployButton {display:none;}
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        
        /* Custom Button Styling - ChatGPT Sidebar List Style */
        .stButton > button {
            background-color: transparent;
            color: #ececf1;
            border: None;
            border-radius: 4px;
            padding: 0.5rem 0.5rem;
            width: 100%;
            text-align: left;
            transition: background-color 0.2s;
            margin-bottom: 2px;
        }
        
        .stButton > button:hover {
            background-color: #2A2B32;
            color: #ececf1;
        }

        .stButton > button:active {
            background-color: #202123;
        }
        
        /* New Chat Button (keep it distinct if needed, or style same) */
        div[data-testid="stSidebar"] div.stButton button[kind="secondary"] {
             border: 1px solid #565869;
             padding: 0.5rem 1rem;
        }

        /* Specific style for Primary Actions if needed */
        button[kind="primary"] {
            background-color: #10a37f !important;
            border: none !important;
        }
        
        button[kind="primary"]:hover {
            background-color: #1a7f64 !important;
        }
        
        /* Clean up the Main Container padding */
        .block-container {
            padding-top: 2rem;
            padding-bottom: 2rem;
        }
        </style>
    """, unsafe_allow_html=True)

